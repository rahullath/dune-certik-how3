"""
Test script for Dune API integration using the dune-client package.
"""
import os
import json
import pandas as pd
from dune_client import DuneClient
# dune-client doesn't have a types module with QueryParameter
from dune_processor import DuneProcessor
from query_builder import DuneQueryBuilder
import protocol_config

# API key (from environment or hardcoded for testing)
API_KEY = os.environ.get("DUNE_API_KEY", "H8Bf9vu6SyWrdVUzUoeluzhXz48ZZyUB")

def test_direct_dune_client():
    """Test the Dune client directly with a query ID."""
    print("Testing direct Dune client...")
    try:
        # Our custom DuneClient doesn't take API_KEY in the constructor
        dune = DuneClient()
        
        # Chainlink EQS query
        query_id = 4953227  # Replace with your actual query ID
        print(f"Fetching results for query ID {query_id}...")
        result_df = dune.execute_query(query_id)
        
        if result_df is not None and not result_df.empty:
            # Print metadata about the result
            print(f"Results fetched successfully. Found {len(result_df)} rows")
            print("\nSample data (first 3 rows):")
            print(result_df.head(3).to_json(orient='records', indent=2))
                
            # Store as CSV
            result_df.to_csv("chainlink_eqs_sample.csv", index=False)
            print(f"\nSaved results to chainlink_eqs_sample.csv")
            
            return result_df
        else:
            print("No results returned or using synthetic data")
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def test_query_builder():
    """Test the query builder by generating queries."""
    print("\nTesting query builder...")
    try:
        builder = DuneQueryBuilder()
        
        # Generate a Chainlink EQS query
        eqs_query = builder.build_query("chainlink", "eqs", months=6)
        print("\nGenerated Chainlink EQS query:")
        print(eqs_query)
        
        # Generate a Uniswap UGS query
        ugs_query = builder.build_query("uniswap", "ugs", months=6)
        print("\nGenerated Uniswap UGS query:")
        print(ugs_query)
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_dune_processor():
    """Test the DuneProcessor with the specified API key."""
    print("\nTesting DuneProcessor...")
    try:
        # Use our custom DuneClient implementation
        processor = DuneProcessor(API_KEY)
        
        # Register a protocol
        processor.register_protocol('chainlink', {
            'eqs': {'query_id': 4953227},
            'ugs': {'query_id': 4953009},
            'category': 'Oracle'
        })
        
        # Fetch data
        print("Fetching Chainlink data...")
        data = processor.fetch_all_protocol_data('chainlink')
        
        # Print summary of fetched data
        for query_type, df in data.items():
            if not df.empty:
                print(f"\n{query_type.upper()} data - {len(df)} rows fetched")
                print("Sample (first 3 rows):")
                print(df.head(3))
            else:
                print(f"\n{query_type.upper()} - No data fetched")
        
        # Calculate scores
        scores = processor.calculate_scores('chainlink', data)
        print("\nCalculated scores:")
        print(json.dumps(scores, indent=2))
        
        return scores
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def test_with_execute_query():
    """Test executing a custom query."""
    print("\nTesting with execute_query...")
    try:
        # Use our custom DuneClient 
        dune = DuneClient()
        builder = DuneQueryBuilder()
        
        # Generate a query using the builder
        eqs_query = builder.build_query("chainlink", "eqs", months=3)
        
        # Execute the custom query
        print("Executing custom query (this may take some time)...")
        result_df = dune.execute_custom_query(eqs_query)
        
        if result_df is not None and not result_df.empty:
            # Print results info
            print(f"Query executed successfully. Found {len(result_df)} rows")
            print("\nSample data (first 3 rows):")
            print(result_df.head(3))
            
            return result_df
        else:
            print("No results returned or using synthetic data")
            return None
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Run tests
    print("=== DUNE API TEST SCRIPT ===")
    print(f"Using API key: {API_KEY[:4]}...{API_KEY[-4:]}")
    
    # Test direct client first
    direct_result = test_direct_dune_client()
    
    # Test query builder
    builder_result = test_query_builder()
    
    # Test processor
    processor_result = test_dune_processor()
    
    # Test with execute_query (optional - commented out to avoid creating new queries)
    # execute_result = test_with_execute_query()
    
    print("\n=== TEST SUMMARY ===")
    print(f"Direct client test: {'Success' if direct_result else 'Failed'}")
    print(f"Query builder test: {'Success' if builder_result else 'Failed'}")
    print(f"Processor test: {'Success' if processor_result else 'Failed'}")
    # print(f"Execute query test: {'Success' if execute_result else 'Failed'}")