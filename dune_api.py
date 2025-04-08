import os
import logging
import time
import requests
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from config import DUNE_API_KEY, DUNE_API_BASE_URL

logger = logging.getLogger(__name__)

class DuneAnalyticsAPI:
    """Client for interacting with the Dune Analytics API."""

    def __init__(self, api_key=None):
        self.api_key = api_key or DUNE_API_KEY
        self.base_url = DUNE_API_BASE_URL
        self.headers = {
            "x-dune-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
    def execute_query(self, query_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a query on Dune Analytics and return the results.

        Args:
            query_id: The ID of the Dune query to execute
            parameters: Optional parameters for the query

        Returns:
            The results of the query as a dictionary
        """
        if not self.api_key:
            logger.error("Dune API key not provided")
            return {"error": "API key not configured"}
        
        # Execute the query
        execution_url = f"{self.base_url}/query/{query_id}/execute"
        
        execution_params = {}
        if parameters:
            execution_params["parameters"] = parameters
        
        try:
            # Request execution
            execution_response = requests.post(
                execution_url, 
                headers=self.headers, 
                json=execution_params
            )
            execution_response.raise_for_status()
            
            # Get the execution ID
            execution_id = execution_response.json().get("execution_id")
            if not execution_id:
                logger.error(f"Failed to get execution ID for query {query_id}")
                return {"error": "Failed to get execution ID"}
            
            # Check execution status and get results
            status_url = f"{self.base_url}/execution/{execution_id}/status"
            
            # Poll for results (with timeout)
            max_attempts = 12  # 2 minutes total (12 * 10 seconds)
            for attempt in range(max_attempts):
                # Get execution status
                status_response = requests.get(status_url, headers=self.headers)
                status_response.raise_for_status()
                
                status_data = status_response.json()
                state = status_data.get("state")
                
                if state == "QUERY_STATE_COMPLETED":
                    # Query completed, get results
                    results_url = f"{self.base_url}/execution/{execution_id}/results"
                    results_response = requests.get(results_url, headers=self.headers)
                    results_response.raise_for_status()
                    
                    return results_response.json()
                elif state in ["QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"]:
                    logger.error(f"Query {query_id} failed or was cancelled. State: {state}")
                    return {"error": f"Query execution failed: {state}"}
                
                # Query still running, wait and try again
                time.sleep(10)
            
            # Timeout reached
            logger.error(f"Query {query_id} execution timed out")
            return {"error": "Query execution timed out"}
            
        except requests.RequestException as e:
            logger.error(f"Error executing query {query_id}: {e}")
            return {"error": f"API request failed: {str(e)}"}
    
    def get_revenue_data(self, query_id: str, protocol: str, months: int = 12) -> List[Dict[str, Any]]:
        """Fetch revenue data for a specific protocol.
        
        Args:
            query_id: The ID of the revenue query for this protocol
            protocol: The name of the protocol
            months: Number of months of data to get
            
        Returns:
            List of monthly revenue data
        """
        today = datetime.utcnow()
        start_date = (today - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        
        parameters = {
            "protocol": protocol,
            "start_date": start_date
        }
        
        results = self.execute_query(query_id, parameters)
        
        if "error" in results:
            logger.error(f"Error getting revenue data for {protocol}: {results['error']}")
            return []
        
        return self._parse_revenue_data(results)
    
    def get_user_data(self, query_id: str, protocol: str, months: int = 12) -> List[Dict[str, Any]]:
        """Fetch user metrics data for a specific protocol.
        
        Args:
            query_id: The ID of the user metrics query for this protocol
            protocol: The name of the protocol
            months: Number of months of data to get
            
        Returns:
            List of monthly user metrics data
        """
        today = datetime.utcnow()
        start_date = (today - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        
        parameters = {
            "protocol": protocol,
            "start_date": start_date
        }
        
        results = self.execute_query(query_id, parameters)
        
        if "error" in results:
            logger.error(f"Error getting user data for {protocol}: {results['error']}")
            return []
        
        return self._parse_user_data(results)
    
    def _parse_revenue_data(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse the revenue data from Dune query results.
        
        Args:
            results: Raw query results from Dune
            
        Returns:
            List of standardized revenue data dictionaries
        """
        revenue_data = []
        
        try:
            # Extract rows from the response
            rows = results.get("result", {}).get("rows", [])
            
            for row in rows:
                month = row.get("month")
                if not month:
                    continue
                
                # Convert to datetime object if it's a string
                if isinstance(month, str):
                    month = datetime.strptime(month, "%Y-%m-%d %H:%M:%S.%f")
                
                data = {
                    "month": month.strftime("%Y-%m-01") if isinstance(month, datetime) else month,
                    "total_fees": row.get("total_fees", 0),
                    "source": row.get("source", ""),
                    "mom_change": row.get("mom_change"),
                }
                revenue_data.append(data)
                
        except Exception as e:
            logger.error(f"Error parsing revenue data: {e}")
        
        return revenue_data
    
    def _parse_user_data(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse the user metrics data from Dune query results.
        
        Args:
            results: Raw query results from Dune
            
        Returns:
            List of standardized user metrics data dictionaries
        """
        user_data = []
        
        try:
            # Extract rows from the response
            rows = results.get("result", {}).get("rows", [])
            
            for row in rows:
                month = row.get("month")
                if not month:
                    continue
                
                # Convert to datetime object if it's a string
                if isinstance(month, str):
                    month = datetime.strptime(month, "%Y-%m-%d %H:%M:%S.%f")
                
                data = {
                    "month": month.strftime("%Y-%m-01") if isinstance(month, datetime) else month,
                    "active_addresses": row.get("active_addresses", 0),
                    "transaction_count": row.get("transaction_count", 0),
                    "transaction_volume": row.get("transaction_volume", 0),
                    "active_address_growth_rate": row.get("active_address_growth_rate"),
                    "transaction_count_growth_rate": row.get("transaction_count_growth_rate"),
                    "transaction_volume_growth_rate": row.get("transaction_volume_growth_rate"),
                    "active_address_percentile": row.get("active_address_percentile"),
                    "transaction_count_percentile": row.get("transaction_count_percentile"),
                    "transaction_volume_percentile": row.get("transaction_volume_percentile")
                }
                user_data.append(data)
                
        except Exception as e:
            logger.error(f"Error parsing user data: {e}")
        
        return user_data

# Sample revenue data SQL query template for Dune
REVENUE_QUERY_TEMPLATE = """
WITH MonthlyFees AS (
  SELECT
    DATE_TRUNC('month', date_start) AS month,
    SUM(usd_amount) AS total_fees,
    '{{source}}' AS source
  FROM {{schema}}.{{table}}
  WHERE
    date_start >= '{{start_date}}'
  GROUP BY 1
), RevenueStability AS (
  SELECT
    month,
    total_fees,
    source,
    LAG(total_fees) OVER (PARTITION BY source ORDER BY month) AS previous_month_fees,
    (
      total_fees - LAG(total_fees) OVER (PARTITION BY source ORDER BY month)
    ) / NULLIF(LAG(total_fees) OVER (PARTITION BY source ORDER BY month), 0) AS mom_change
  FROM MonthlyFees
)
SELECT
  month,
  source,
  total_fees,
  mom_change
FROM RevenueStability
ORDER BY
  month DESC
"""

# Sample user metrics SQL query template for Dune
USER_METRICS_QUERY_TEMPLATE = """
WITH monthly_active_addresses AS (
  SELECT
    DATE_TRUNC('month', evt_block_time) AS month,
    COUNT(DISTINCT evt_tx_from) AS active_addresses
  FROM {{table}}
  WHERE
    evt_block_time >= '{{start_date}}'
  GROUP BY 1
), transaction_count_volume AS (
  SELECT
    DATE_TRUNC('month', evt_block_time) AS month,
    COUNT(*) AS transaction_count,
    SUM(value) AS transaction_volume
  FROM {{table}}
  WHERE
    evt_block_time >= '{{start_date}}'
  GROUP BY 1
), growth_rates AS (
  SELECT
    m1.month,
    m1.active_addresses,
    m2.active_addresses AS previous_active_addresses,
    (
      m1.active_addresses - m2.active_addresses
    ) / NULLIF(m2.active_addresses, 0) * 100 AS active_address_growth_rate,
    t1.transaction_count,
    t2.transaction_count AS previous_transaction_count,
    (
      t1.transaction_count - t2.transaction_count
    ) / NULLIF(t2.transaction_count, 0) * 100 AS transaction_count_growth_rate,
    t1.transaction_volume,
    t2.transaction_volume AS previous_transaction_volume,
    (
      t1.transaction_volume - t2.transaction_volume
    ) / NULLIF(t2.transaction_volume, 0) * 100 AS transaction_volume_growth_rate
  FROM monthly_active_addresses AS m1
  LEFT JOIN monthly_active_addresses AS m2
    ON m1.month = m2.month + INTERVAL '1' MONTH
  LEFT JOIN transaction_count_volume AS t1
    ON m1.month = t1.month
  LEFT JOIN transaction_count_volume AS t2
    ON t1.month = t2.month + INTERVAL '1' MONTH
), percentile_ranking AS (
  SELECT
    month,
    active_addresses,
    transaction_count,
    transaction_volume,
    PERCENT_RANK() OVER (ORDER BY active_addresses) AS active_address_percentile,
    PERCENT_RANK() OVER (ORDER BY transaction_count) AS transaction_count_percentile,
    PERCENT_RANK() OVER (ORDER BY transaction_volume) AS transaction_volume_percentile
  FROM growth_rates
)
SELECT
  *
FROM percentile_ranking
ORDER BY
  month DESC
"""
