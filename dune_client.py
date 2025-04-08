import os
import requests
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config import get_config

logger = logging.getLogger(__name__)

class DuneClient:
    """Client for interacting with Dune Analytics API"""
    
    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.DUNE_API_KEY
        self.base_url = self.config.DUNE_API_BASE_URL
        self.headers = {
            "x-dune-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def execute_query(self, query_id):
        """Execute a query on Dune Analytics and return results"""
        if not self.api_key:
            logger.warning("Dune API key not found. Using synthetic data for testing.")
            return None
        
        try:
            # Start query execution
            execution_url = f"{self.base_url}/query/{query_id}/execute"
            response = requests.post(execution_url, headers=self.headers)
            response.raise_for_status()
            
            execution_id = response.json().get("execution_id")
            if not execution_id:
                logger.error(f"Failed to get execution ID for query {query_id}")
                return None
            
            # Check execution status and get results
            status_url = f"{self.base_url}/execution/{execution_id}/status"
            results_url = f"{self.base_url}/execution/{execution_id}/results"
            
            # Poll for results with exponential backoff
            max_attempts = 10
            wait_time = 2
            
            for attempt in range(max_attempts):
                time.sleep(wait_time)
                wait_time *= 1.5  # Exponential backoff
                
                status_response = requests.get(status_url, headers=self.headers)
                status_response.raise_for_status()
                
                status = status_response.json().get("state")
                if status == "QUERY_STATE_COMPLETED":
                    results_response = requests.get(results_url, headers=self.headers)
                    results_response.raise_for_status()
                    
                    result_data = results_response.json().get("result", {}).get("rows", [])
                    return pd.DataFrame(result_data)
                
                elif status in ["QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"]:
                    logger.error(f"Query {query_id} failed with status: {status}")
                    return None
            
            logger.error(f"Query {query_id} did not complete within the allowed time")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error executing Dune query {query_id}: {str(e)}")
            return None
    
    def execute_custom_query(self, query_text):
        """Execute a custom SQL query on Dune Analytics"""
        if not self.api_key:
            logger.warning("Dune API key not found. Using synthetic data for testing.")
            return None
        
        try:
            # Create a new query
            create_url = f"{self.base_url}/query/new"
            create_payload = {
                "query": query_text,
                "name": f"How3.io Query {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            create_response = requests.post(create_url, headers=self.headers, json=create_payload)
            create_response.raise_for_status()
            
            query_id = create_response.json().get("query_id")
            if not query_id:
                logger.error("Failed to create custom query")
                return None
            
            # Execute the created query
            return self.execute_query(query_id)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error executing custom Dune query: {str(e)}")
            return None
    
    def get_monthly_revenue_data(self, protocol, months=12):
        """Get monthly revenue data for a protocol"""
        # Try to get real data from Dune
        from query_templates import get_revenue_query
        query_text = get_revenue_query(protocol, months)
        
        # If we have an API key, try to execute the query
        if self.api_key:
            result = self.execute_custom_query(query_text)
            if result is not None and not result.empty:
                return result
        
        # Otherwise, generate synthetic data for testing purposes
        logger.info(f"Using synthetic revenue data for {protocol}")
        return self._generate_synthetic_revenue_data(protocol, months)
    
    def get_user_growth_data(self, protocol, months=12):
        """Get monthly user growth data for a protocol"""
        # Try to get real data from Dune
        from query_templates import get_user_growth_query
        query_text = get_user_growth_query(protocol, months)
        
        # If we have an API key, try to execute the query
        if self.api_key:
            result = self.execute_custom_query(query_text)
            if result is not None and not result.empty:
                return result
        
        # Otherwise, generate synthetic data for testing purposes
        logger.info(f"Using synthetic user growth data for {protocol}")
        return self._generate_synthetic_user_data(protocol, months)
    
    def _generate_synthetic_revenue_data(self, protocol, months):
        """Generate synthetic revenue data for testing"""
        protocol_map = {
            "chainlink": {"base": 5000000, "growth": 0.05, "volatility": 0.2},
            "uniswap": {"base": 8000000, "growth": 0.03, "volatility": 0.15},
            "aave": {"base": 3000000, "growth": 0.02, "volatility": 0.1},
            # Default values for other protocols
            "default": {"base": 1000000, "growth": 0.01, "volatility": 0.1}
        }
        
        profile = protocol_map.get(protocol.lower(), protocol_map["default"])
        base_revenue = profile["base"]
        monthly_growth = profile["growth"]
        volatility = profile["volatility"]
        
        today = datetime.now()
        data = []
        mom_changes = []
        
        for i in range(months):
            month_date = today - timedelta(days=30*i)
            month_str = month_date.strftime("%Y-%m-01")
            
            # Generate revenue with growth trend and some volatility
            trend_factor = (1 + monthly_growth) ** (months - i)
            random_factor = 1 + np.random.uniform(-volatility, volatility)
            monthly_revenue = base_revenue * trend_factor * random_factor
            
            # Calculate month-over-month change if not the first month
            mom_change = None
            if i > 0:
                prev_month = data[-1]["total_fees"]
                mom_change = (monthly_revenue - prev_month) / prev_month
                mom_changes.append(mom_change)
            
            data.append({
                "month": month_str,
                "total_fees": monthly_revenue,
                "source": "total",
                "mom_change": mom_change
            })
        
        # Add stability and magnitude scores
        avg_mom_change = np.mean(mom_changes) if mom_changes else 0
        stddev_mom_change = np.std(mom_changes) if mom_changes else 0
        
        # Add these metrics to all rows
        for row in data:
            row["avg_mom_change"] = avg_mom_change
            row["stddev_mom_change"] = stddev_mom_change
            row["num_months"] = len(mom_changes)
        
        # Convert to pandas DataFrame and reverse order (oldest first)
        df = pd.DataFrame(data[::-1])
        return df
    
    def _generate_synthetic_user_data(self, protocol, months):
        """Generate synthetic user growth data for testing"""
        protocol_map = {
            "chainlink": {"addresses": 50000, "txs": 500000, "volume": 100000000},
            "uniswap": {"addresses": 100000, "txs": 2000000, "volume": 500000000},
            "aave": {"addresses": 30000, "txs": 300000, "volume": 200000000},
            # Default values for other protocols
            "default": {"addresses": 20000, "txs": 200000, "volume": 50000000}
        }
        
        profile = protocol_map.get(protocol.lower(), protocol_map["default"])
        base_addresses = profile["addresses"]
        base_txs = profile["txs"]
        base_volume = profile["volume"]
        
        today = datetime.now()
        data = []
        
        for i in range(months):
            month_date = today - timedelta(days=30*i)
            month_str = month_date.strftime("%Y-%m-01")
            
            # Generate metrics with growth trend and some randomness
            trend_factor = 1 + 0.05 * (months - i) / months
            addr_random = 1 + np.random.uniform(-0.1, 0.1)
            tx_random = 1 + np.random.uniform(-0.15, 0.15)
            vol_random = 1 + np.random.uniform(-0.2, 0.2)
            
            active_addresses = int(base_addresses * trend_factor * addr_random)
            transaction_count = int(base_txs * trend_factor * tx_random)
            transaction_volume = base_volume * trend_factor * vol_random
            
            # Calculate growth rates if not the first month
            addr_growth = None
            tx_count_growth = None
            tx_volume_growth = None
            
            if i > 0:
                prev = data[-1]
                addr_growth = 100 * (active_addresses - prev["active_addresses"]) / prev["active_addresses"]
                tx_count_growth = 100 * (transaction_count - prev["transaction_count"]) / prev["transaction_count"]
                tx_volume_growth = 100 * (transaction_volume - prev["transaction_volume"]) / prev["transaction_volume"]
            
            data.append({
                "month": month_str,
                "active_addresses": active_addresses,
                "transaction_count": transaction_count,
                "transaction_volume": transaction_volume,
                "active_address_growth_rate": addr_growth,
                "transaction_count_growth_rate": tx_count_growth,
                "transaction_volume_growth_rate": tx_volume_growth
            })
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data[::-1])
        
        # Calculate percentile rankings
        df['active_address_percentile'] = df['active_addresses'].rank(pct=True)
        df['transaction_count_percentile'] = df['transaction_count'].rank(pct=True)
        df['transaction_volume_percentile'] = df['transaction_volume'].rank(pct=True)
        
        return df
