#!/usr/bin/env python
"""
Command-line tool for fetching Dune Analytics data and calculating scores for crypto protocols.
"""
import os
import sys
import argparse
import logging
import json
import pandas as pd
from datetime import datetime
from dune_processor import DuneProcessor
from protocol_config import PROTOCOL_CONFIGS, CATEGORY_SETTINGS, SCORE_WEIGHTS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scoring.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_arg_parser():
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description='Fetch data and calculate scores for crypto protocols')
    
    parser.add_argument(
        '--protocol', '-p', 
        type=str,
        help='Protocol name to process (omit to process all registered protocols)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='scores',
        help='Output directory for results (default: "scores")'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['csv', 'json', 'both'],
        default='both',
        help='Output format (default: both csv and json)'
    )
    
    parser.add_argument(
        '--api-key', '-k',
        type=str,
        help='Dune Analytics API key (defaults to DUNE_API_KEY environment variable)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser

def save_results(protocol_name, data, scores, output_dir, format_type):
    """Save results to file(s)"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Format timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"{protocol_name}_{timestamp}"
    
    # Save scores
    if format_type in ['json', 'both']:
        score_file = os.path.join(output_dir, f"{base_filename}_scores.json")
        with open(score_file, 'w') as f:
            json.dump(scores, f, indent=2)
        logger.info(f"Saved scores to {score_file}")
    
    if format_type in ['csv', 'both']:
        score_file = os.path.join(output_dir, f"{base_filename}_scores.csv")
        pd.DataFrame([scores]).to_csv(score_file, index=False)
        logger.info(f"Saved scores to {score_file}")
    
    # Save raw data for each query type
    for query_type, df in data.items():
        if not df.empty:
            if format_type in ['csv', 'both']:
                data_file = os.path.join(output_dir, f"{base_filename}_{query_type}_data.csv")
                df.to_csv(data_file, index=False)
                logger.info(f"Saved {query_type} data to {data_file}")
            
            if format_type in ['json', 'both']:
                data_file = os.path.join(output_dir, f"{base_filename}_{query_type}_data.json")
                df.to_json(data_file, orient='records', indent=2)
                logger.info(f"Saved {query_type} data to {data_file}")

def main():
    """Main entry point"""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("DUNE_API_KEY")
    if not api_key:
        logger.error("No Dune API key provided. Use --api-key or set DUNE_API_KEY environment variable.")
        sys.exit(1)
    
    # Initialize processor
    processor = DuneProcessor(api_key)
    
    # Register all protocols from config
    for protocol_name, config in PROTOCOL_CONFIGS.items():
        processor.register_protocol(protocol_name, config)
    
    # Determine which protocols to process
    if args.protocol:
        protocol_names = [args.protocol.lower()]
        if protocol_names[0] not in PROTOCOL_CONFIGS:
            logger.error(f"Protocol '{args.protocol}' not found in configuration")
            sys.exit(1)
    else:
        protocol_names = list(PROTOCOL_CONFIGS.keys())
    
    # Process each protocol
    all_scores = {}
    for protocol_name in protocol_names:
        logger.info(f"Processing {protocol_name}...")
        
        try:
            # Fetch data
            data = processor.fetch_all_protocol_data(protocol_name)
            
            if not data:
                logger.warning(f"No data fetched for {protocol_name}")
                continue
            
            # Calculate scores
            scores = processor.calculate_scores(protocol_name, data)
            all_scores[protocol_name] = scores
            
            # Save individual protocol results
            save_results(protocol_name, data, scores, args.output, args.format)
            
            logger.info(f"Completed processing {protocol_name}")
            logger.info(f"Scores: {scores}")
            
        except Exception as e:
            logger.error(f"Error processing {protocol_name}: {str(e)}", exc_info=True)
    
    # Save combined results
    if len(all_scores) > 1:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if args.format in ['json', 'both']:
            combined_file = os.path.join(args.output, f"all_protocols_{timestamp}.json")
            with open(combined_file, 'w') as f:
                json.dump(all_scores, f, indent=2)
            logger.info(f"Saved combined scores to {combined_file}")
        
        if args.format in ['csv', 'both']:
            # Convert to DataFrame for CSV
            rows = []
            for protocol, scores in all_scores.items():
                # Create a new dictionary with protocol name and all scores
                row = {'protocol': protocol}
                # Safely copy values from scores dict to row
                for k, v in scores.items():
                    row[k] = v
                rows.append(row)
            
            combined_file = os.path.join(args.output, f"all_protocols_{timestamp}.csv")
            pd.DataFrame(rows).to_csv(combined_file, index=False)
            logger.info(f"Saved combined scores to {combined_file}")
    
    logger.info("Processing complete")

if __name__ == "__main__":
    main()