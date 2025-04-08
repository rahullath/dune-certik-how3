"""
Utility for building and validating Dune Analytics queries for different protocols.
This helps generate SQL queries that can be run in Dune's interface to create dashboards.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuneQueryBuilder:
    """Helper class to build and validate Dune Analytics queries."""
    
    def __init__(self):
        """Initialize the query builder."""
        # Base templates for different query types
        self.templates = {
            'eqs': self._load_eqs_template(),
            'ugs': self._load_ugs_template(),
            'fvs': self._load_fvs_template()
        }
        
        # Protocol-specific table mappings
        self.protocol_tables = {}
        
        # Load protocol table configurations if available
        config_path = 'protocol_tables.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.protocol_tables = json.load(f)
                logger.info(f"Loaded protocol tables from {config_path}")
            except Exception as e:
                logger.error(f"Error loading protocol tables: {str(e)}")
    
    def _load_eqs_template(self) -> str:
        """Load template for Earnings Quality Score queries."""
        return """
WITH MonthlyFees AS (
  SELECT
    DATE_TRUNC('month', {timestamp_col}) AS month,
    SUM({fee_amount_col}) AS total_fees,
    '{source}' AS source
  FROM {protocol_schema}.{revenue_table}
  WHERE
    {timestamp_col} >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where}
  GROUP BY
    1
  {union_clauses}
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
), StabilityMagnitudeScores AS (
  SELECT
    source,
    AVG(mom_change) AS avg_mom_change,
    STDDEV(mom_change) AS stddev_mom_change,
    COUNT(*) AS num_months
  FROM RevenueStability
  GROUP BY
    source
)
SELECT
  month,
  source,
  total_fees,
  mom_change,
  avg_mom_change,
  stddev_mom_change,
  num_months
FROM RevenueStability
JOIN StabilityMagnitudeScores
  USING (source)
ORDER BY
  month DESC,
  source
"""
    
    def _load_ugs_template(self) -> str:
        """Load template for User Growth Score queries."""
        return """
WITH monthly_active_addresses AS (
  SELECT
    DATE_TRUNC('month', {timestamp_col}) AS month,
    COUNT(DISTINCT {user_address_col}) AS active_addresses
  FROM {protocol_schema}.{user_table}
  WHERE
    {timestamp_col} >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where}
  GROUP BY
    1
), transaction_count_volume AS (
  SELECT
    DATE_TRUNC('month', {timestamp_col}) AS month,
    COUNT(*) AS transaction_count,
    SUM({amount_col}) AS transaction_volume
  FROM {protocol_schema}.{transaction_table}
  WHERE
    {timestamp_col} >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where}
  GROUP BY
    1
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
    active_address_growth_rate,
    transaction_count_growth_rate,
    transaction_volume_growth_rate,
    PERCENT_RANK() OVER (ORDER BY active_addresses) AS active_address_percentile,
    PERCENT_RANK() OVER (ORDER BY transaction_count) AS transaction_count_percentile,
    PERCENT_RANK() OVER (ORDER BY transaction_volume) AS transaction_volume_percentile
  FROM growth_rates
)
SELECT
  month,
  active_addresses,
  transaction_count,
  transaction_volume,
  active_address_growth_rate,
  transaction_count_growth_rate,
  transaction_volume_growth_rate,
  active_address_percentile,
  transaction_count_percentile,
  transaction_volume_percentile
FROM percentile_ranking
ORDER BY
  month DESC
"""
    
    def _load_fvs_template(self) -> str:
        """Load template for Fair Value Score queries."""
        return """
-- This is an example FVS query template
-- You may need to customize this based on the specific metrics needed
WITH monthly_metrics AS (
  SELECT
    DATE_TRUNC('month', CURRENT_DATE) AS month,
    {market_cap_value} AS market_cap,
    
    -- Annual revenue calculation based on most recent months
    (
      SELECT SUM(total_fees)
      FROM (
        SELECT
          DATE_TRUNC('month', {timestamp_col}) AS fee_month,
          SUM({fee_amount_col}) AS total_fees
        FROM {protocol_schema}.{revenue_table}
        WHERE
          {timestamp_col} >= CURRENT_DATE - INTERVAL '12' month
          {additional_where}
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 12
      ) recent_revenues
    ) AS annual_revenue
)
SELECT
  month,
  market_cap,
  annual_revenue,
  -- Calculate P/S ratio (Market Cap to Annual Revenue)
  CASE
    WHEN annual_revenue > 0 THEN market_cap / annual_revenue
    ELSE NULL
  END AS ps_ratio
FROM
  monthly_metrics
"""
    
    def build_query(self, protocol: str, query_type: str, months: int = 12) -> str:
        """
        Build a query for a specific protocol and type.
        
        Args:
            protocol: Protocol name (e.g., 'chainlink')
            query_type: Type of query ('eqs', 'ugs', 'fvs')
            months: Number of months of data to retrieve
            
        Returns:
            SQL query string for Dune Analytics
        """
        if query_type not in self.templates:
            raise ValueError(f"Unknown query type: {query_type}")
        
        # Get protocol-specific table mappings
        if protocol not in self.protocol_tables:
            logger.warning(f"No table mapping found for {protocol}. Using generic placeholders.")
            tables = self._get_default_tables(protocol)
        else:
            tables = self.protocol_tables[protocol]
        
        # Apply protocol-specific table mappings to template
        template = self.templates[query_type]
        
        if query_type == 'eqs':
            return self._build_eqs_query(protocol, template, tables, months)
        elif query_type == 'ugs':
            return self._build_ugs_query(protocol, template, tables, months)
        elif query_type == 'fvs':
            return self._build_fvs_query(protocol, template, tables, months)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _build_eqs_query(self, protocol: str, template: str, tables: Dict[str, Any], months: int) -> str:
        """Build an EQS query using the template and protocol-specific tables."""
        # Extract table config for EQS
        revenue_sources = tables.get('revenue_sources', [{'name': 'total'}])
        
        # Create UNION ALL clauses for multiple revenue sources
        union_clauses = []
        for i, source in enumerate(revenue_sources[1:], 1):  # Skip first source (included in main query)
            source_name = source.get('name', f'source_{i}')
            source_table = source.get('table', tables.get('revenue_table', f'{protocol}_revenue'))
            source_schema = source.get('schema', tables.get('protocol_schema', protocol))
            timestamp_col = source.get('timestamp_col', tables.get('timestamp_col', 'block_time'))
            fee_amount_col = source.get('fee_amount_col', tables.get('fee_amount_col', 'fee_usd'))
            additional_where = source.get('additional_where', tables.get('additional_where', ''))
            
            # Format the additional WHERE clause if present
            if additional_where and not additional_where.strip().startswith('AND'):
                additional_where = f"AND {additional_where}"
            
            union_clause = f"""
  UNION ALL
  SELECT
    DATE_TRUNC('month', {timestamp_col}) AS month,
    SUM({fee_amount_col}) AS total_fees,
    '{source_name}' AS source
  FROM {source_schema}.{source_table}
  WHERE
    {timestamp_col} >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where}
  GROUP BY
    1"""
            union_clauses.append(union_clause)
        
        # Get default values for main query
        main_source = revenue_sources[0] if revenue_sources else {}
        source_name = main_source.get('name', 'total')
        revenue_table = main_source.get('table', tables.get('revenue_table', f'{protocol}_revenue'))
        protocol_schema = main_source.get('schema', tables.get('protocol_schema', protocol))
        timestamp_col = main_source.get('timestamp_col', tables.get('timestamp_col', 'block_time'))
        fee_amount_col = main_source.get('fee_amount_col', tables.get('fee_amount_col', 'fee_usd'))
        additional_where = main_source.get('additional_where', tables.get('additional_where', ''))
        
        # Format the additional WHERE clause if present
        if additional_where and not additional_where.strip().startswith('AND'):
            additional_where = f"AND {additional_where}"
        
        # Build the query by substituting values
        query = template.format(
            protocol_schema=protocol_schema,
            revenue_table=revenue_table,
            timestamp_col=timestamp_col,
            fee_amount_col=fee_amount_col,
            source=source_name,
            months=months,
            additional_where=additional_where,
            union_clauses=''.join(union_clauses)
        )
        
        return query
    
    def _build_ugs_query(self, protocol: str, template: str, tables: Dict[str, Any], months: int) -> str:
        """Build a UGS query using the template and protocol-specific tables."""
        # Extract table config for UGS
        protocol_schema = tables.get('protocol_schema', protocol)
        user_table = tables.get('user_table', f'{protocol}_users')
        transaction_table = tables.get('transaction_table', f'{protocol}_transactions')
        timestamp_col = tables.get('timestamp_col', 'block_time')
        user_address_col = tables.get('user_address_col', 'user_address')
        amount_col = tables.get('amount_col', 'amount_usd')
        additional_where = tables.get('additional_where', '')
        
        # Format the additional WHERE clause if present
        if additional_where and not additional_where.strip().startswith('AND'):
            additional_where = f"AND {additional_where}"
        
        # Build the query by substituting values
        query = template.format(
            protocol_schema=protocol_schema,
            user_table=user_table,
            transaction_table=transaction_table,
            timestamp_col=timestamp_col,
            user_address_col=user_address_col,
            amount_col=amount_col,
            months=months,
            additional_where=additional_where
        )
        
        return query
    
    def _build_fvs_query(self, protocol: str, template: str, tables: Dict[str, Any], months: int) -> str:
        """Build an FVS query using the template and protocol-specific tables."""
        # Extract table config for FVS
        protocol_schema = tables.get('protocol_schema', protocol)
        revenue_table = tables.get('revenue_table', f'{protocol}_revenue')
        timestamp_col = tables.get('timestamp_col', 'block_time')
        fee_amount_col = tables.get('fee_amount_col', 'fee_usd')
        market_cap_value = tables.get('market_cap_value', '0')
        additional_where = tables.get('additional_where', '')
        
        # Format the additional WHERE clause if present
        if additional_where and not additional_where.strip().startswith('AND'):
            additional_where = f"AND {additional_where}"
        
        # Build the query by substituting values
        query = template.format(
            protocol_schema=protocol_schema,
            revenue_table=revenue_table,
            timestamp_col=timestamp_col,
            fee_amount_col=fee_amount_col,
            market_cap_value=market_cap_value,
            months=months,
            additional_where=additional_where
        )
        
        return query
    
    def _get_default_tables(self, protocol: str) -> Dict[str, Any]:
        """Get default table mappings for a protocol."""
        return {
            'protocol_schema': protocol,
            'revenue_table': f'{protocol}_revenue',
            'user_table': f'{protocol}_users',
            'transaction_table': f'{protocol}_transactions',
            'timestamp_col': 'block_time',
            'fee_amount_col': 'fee_usd',
            'user_address_col': 'user_address',
            'amount_col': 'amount_usd',
            'market_cap_value': '0',
            'revenue_sources': [{'name': 'total'}]
        }
    
    def save_protocol_tables(self, filepath: str = 'protocol_tables.json'):
        """Save the current protocol table mappings to a file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.protocol_tables, f, indent=2)
            logger.info(f"Saved protocol table mappings to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving protocol table mappings: {str(e)}")
            return False
    
    def add_protocol_tables(self, protocol: str, tables: Dict[str, Any]):
        """Add or update table mappings for a protocol."""
        self.protocol_tables[protocol] = tables
        logger.info(f"Added table mappings for {protocol}")
    
    def get_protocol_tables(self, protocol: str) -> Dict[str, Any]:
        """Get table mappings for a specific protocol."""
        return self.protocol_tables.get(protocol, self._get_default_tables(protocol))


if __name__ == "__main__":
    # Example usage
    builder = DuneQueryBuilder()
    
    # Define table mappings for Chainlink
    chainlink_tables = {
        'protocol_schema': 'chainlink',
        'revenue_sources': [
            {
                'name': 'vrf',
                'table': 'vrf_reward_daily',
                'timestamp_col': 'date_start',
                'fee_amount_col': 'usd_amount'
            },
            {
                'name': 'automation',
                'table': 'automation_reward_daily',
                'timestamp_col': 'date_start',
                'fee_amount_col': 'usd_amount'
            },
            {
                'name': 'fm',
                'table': 'fm_reward_daily',
                'timestamp_col': 'date_start',
                'fee_amount_col': 'usd_amount'
            },
            {
                'name': 'ocr',
                'table': 'ocr_reward_daily',
                'timestamp_col': 'date_start',
                'fee_amount_col': 'usd_amount'
            },
            {
                'name': 'ccip',
                'table': 'ccip_reward_daily',
                'timestamp_col': 'date_start',
                'fee_amount_col': 'usd_amount'
            }
        ],
        'user_table': 'linktoken_evt_transfer',
        'transaction_table': 'linktoken_evt_transfer',
        'user_address_col': 'evt_tx_from',
        'timestamp_col': 'evt_block_time',
        'amount_col': 'value'
    }
    
    # Add Chainlink table mappings
    builder.add_protocol_tables('chainlink', chainlink_tables)
    
    # Build a query for Chainlink EQS
    eqs_query = builder.build_query('chainlink', 'eqs', months=12)
    print("CHAINLINK EQS QUERY:")
    print(eqs_query)
    print("\n")
    
    # Build a query for Chainlink UGS
    ugs_query = builder.build_query('chainlink', 'ugs', months=12)
    print("CHAINLINK UGS QUERY:")
    print(ugs_query)
    
    # Save the protocol table mappings
    builder.save_protocol_tables()