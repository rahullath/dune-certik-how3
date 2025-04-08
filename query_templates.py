"""
Standard query templates for different protocol metrics.
These templates can be customized per protocol using placeholders.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

# Template for Earnings Quality Score (EQS) queries
EQS_TEMPLATE = """
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

# Template for User Growth Score (UGS) queries
UGS_TEMPLATE = """
WITH user_chains AS (
  {user_chain_queries}
), 
monthly_active_addresses AS (
  SELECT
    DATE_TRUNC('month', evt_block_time) AS month,
    COUNT(DISTINCT evt_tx_from) AS active_addresses
  FROM user_chains
  WHERE
    evt_block_time >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where}
  GROUP BY
    1
), transaction_count_volume AS (
  SELECT
    DATE_TRUNC('month', evt_block_time) AS month,
    COUNT(*) AS transaction_count,
    SUM(value) AS transaction_volume
  FROM user_chains
  WHERE
    evt_block_time >= CURRENT_DATE - INTERVAL '{months}' month
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

# Template for Fair Value Score (FVS) queries
FVS_TEMPLATE = """
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

# Template for Safety Score (SS) queries
# Note: This is just a placeholder template and needs to be customized
# once we have actual security data from providers like Certik
SS_TEMPLATE = """
SELECT
  DATE_TRUNC('month', CURRENT_DATE) AS month,
  {protocol_name} AS protocol,
  {security_metrics_subquery} AS security_score
"""

# Helper function to build multi-chain UGS query
def build_user_chain_queries(chains):
    """
    Build the chain-specific subqueries for the UGS template.
    
    Args:
        chains: List of dictionaries with chain-specific table info
        
    Returns:
        SQL string with UNION ALL subqueries
    """
    queries = []
    
    for i, chain in enumerate(chains):
        schema = chain.get('schema')
        table = chain.get('table')
        user_col = chain.get('user_address_col', 'evt_tx_from')
        time_col = chain.get('timestamp_col', 'evt_block_time')
        amount_col = chain.get('amount_col', 'value')
        
        query = f"""
    {'SELECT' if i == 0 else 'UNION ALL SELECT'}
      {user_col} AS evt_tx_from,
      {time_col} AS evt_block_time,
      {amount_col} AS value
    FROM {schema}.{table}"""
        
        queries.append(query)
    
    return "\n".join(queries)

# Functions required by the existing DuneClient implementation
def get_revenue_query(protocol, months=12):
    """
    Generate a revenue query for a specific protocol.
    
    Args:
        protocol: Protocol name (e.g., 'chainlink')
        months: Number of months to analyze
        
    Returns:
        SQL query string for revenue data
    """
    try:
        # Get protocol configuration
        protocol_data = None
        protocol_tables_path = "protocol_tables.json"
        
        if os.path.exists(protocol_tables_path):
            with open(protocol_tables_path, 'r') as f:
                all_protocol_data = json.load(f)
                protocol_data = all_protocol_data.get(protocol.lower())
        
        if not protocol_data:
            logger.warning(f"No configuration found for {protocol}. Using default template.")
            return f"""
            -- Default revenue query for {protocol}
            SELECT
                DATE_TRUNC('month', block_time) AS month,
                SUM(fee_usd) AS total_fees,
                '{protocol}' AS source
            FROM {protocol}.revenue
            WHERE
                block_time >= CURRENT_DATE - INTERVAL '{months}' month
            GROUP BY 1
            ORDER BY 1 DESC
            """
        
        # Build query based on protocol configuration
        if 'revenue_sources' in protocol_data:
            # Multiple revenue sources
            sources = protocol_data['revenue_sources']
            
            # Use EQS template with the first source as the primary query
            primary_source = sources[0]
            
            source_name = primary_source.get('name', 'total')
            schema = primary_source.get('schema', protocol)
            table = primary_source.get('table', 'revenue')
            timestamp_col = primary_source.get('timestamp_col', 'block_time')
            fee_amount_col = primary_source.get('fee_amount_col', 'fee_usd')
            additional_where = primary_source.get('additional_where', '')
            
            # Format additional WHERE if present
            if additional_where and not additional_where.strip().startswith('AND'):
                additional_where = f"AND {additional_where}"
            
            # Build union clauses for other sources
            union_clauses = []
            for i, source in enumerate(sources[1:], 1):
                source_name_i = source.get('name', f'source_{i}')
                schema_i = source.get('schema', protocol)
                table_i = source.get('table', 'revenue')
                timestamp_col_i = source.get('timestamp_col', 'block_time')
                fee_amount_col_i = source.get('fee_amount_col', 'fee_usd')
                additional_where_i = source.get('additional_where', '')
                
                # Format additional WHERE if present
                if additional_where_i and not additional_where_i.strip().startswith('AND'):
                    additional_where_i = f"AND {additional_where_i}"
                
                union_clause = f"""
  UNION ALL
  SELECT
    DATE_TRUNC('month', {timestamp_col_i}) AS month,
    SUM({fee_amount_col_i}) AS total_fees,
    '{source_name_i}' AS source
  FROM {schema_i}.{table_i}
  WHERE
    {timestamp_col_i} >= CURRENT_DATE - INTERVAL '{months}' month
    {additional_where_i}
  GROUP BY
    1"""
                union_clauses.append(union_clause)
            
            # Format the main query
            query = EQS_TEMPLATE.format(
                protocol_schema=schema,
                revenue_table=table,
                timestamp_col=timestamp_col,
                fee_amount_col=fee_amount_col,
                source=source_name,
                months=months,
                additional_where=additional_where,
                union_clauses=''.join(union_clauses)
            )
            
            return query
        else:
            # Simple revenue query (single source)
            schema = protocol_data.get('protocol_schema', protocol)
            table = protocol_data.get('revenue_table', 'revenue')
            timestamp_col = protocol_data.get('timestamp_col', 'block_time')
            fee_amount_col = protocol_data.get('fee_amount_col', 'fee_usd')
            additional_where = protocol_data.get('additional_where', '')
            
            # Format additional WHERE if present
            if additional_where and not additional_where.strip().startswith('AND'):
                additional_where = f"AND {additional_where}"
            
            # Format the query
            query = EQS_TEMPLATE.format(
                protocol_schema=schema,
                revenue_table=table,
                timestamp_col=timestamp_col,
                fee_amount_col=fee_amount_col,
                source=protocol,
                months=months,
                additional_where=additional_where,
                union_clauses=''
            )
            
            return query
    
    except Exception as e:
        logger.error(f"Error generating revenue query for {protocol}: {str(e)}")
        return f"""
        -- Fallback revenue query for {protocol} (error occurred during query generation)
        SELECT
            DATE_TRUNC('month', CURRENT_DATE) AS month,
            0 AS total_fees,
            '{protocol}' AS source,
            0 AS mom_change,
            0 AS avg_mom_change,
            0 AS stddev_mom_change,
            0 AS num_months
        """

def get_user_growth_query(protocol, months=12):
    """
    Generate a user growth query for a specific protocol.
    
    Args:
        protocol: Protocol name (e.g., 'chainlink')
        months: Number of months to analyze
        
    Returns:
        SQL query string for user growth data
    """
    try:
        # Get protocol configuration
        protocol_data = None
        protocol_tables_path = "protocol_tables.json"
        
        if os.path.exists(protocol_tables_path):
            with open(protocol_tables_path, 'r') as f:
                all_protocol_data = json.load(f)
                protocol_data = all_protocol_data.get(protocol.lower())
        
        if not protocol_data:
            logger.warning(f"No configuration found for {protocol}. Using default template.")
            return f"""
            -- Default user growth query for {protocol}
            WITH monthly_data AS (
                SELECT
                    DATE_TRUNC('month', block_time) AS month,
                    COUNT(DISTINCT user_address) AS active_addresses,
                    COUNT(*) AS transaction_count,
                    SUM(amount_usd) AS transaction_volume
                FROM {protocol}.transactions
                WHERE
                    block_time >= CURRENT_DATE - INTERVAL '{months}' month
                GROUP BY 1
                ORDER BY 1 DESC
            )
            SELECT
                month,
                active_addresses,
                transaction_count,
                transaction_volume,
                NULL AS active_address_growth_rate,
                NULL AS transaction_count_growth_rate,
                NULL AS transaction_volume_growth_rate,
                NULL AS active_address_percentile,
                NULL AS transaction_count_percentile,
                NULL AS transaction_volume_percentile
            FROM monthly_data
            """
        
        # Build query based on protocol configuration
        if 'user_addresses' in protocol_data:
            # Get user chain specifications
            user_chains = protocol_data['user_addresses']
            
            # Generate chain queries
            user_chain_queries = build_user_chain_queries(user_chains)
            additional_where = protocol_data.get('additional_where', '')
            
            # Format additional WHERE if present
            if additional_where and not additional_where.strip().startswith('AND'):
                additional_where = f"AND {additional_where}"
            
            # Format the query
            query = UGS_TEMPLATE.format(
                user_chain_queries=user_chain_queries,
                months=months,
                additional_where=additional_where
            )
            
            return query
        else:
            # Simple user growth query (single source)
            schema = protocol_data.get('protocol_schema', protocol)
            user_table = protocol_data.get('user_table', 'users')
            transaction_table = protocol_data.get('transaction_table', 'transactions')
            timestamp_col = protocol_data.get('timestamp_col', 'block_time')
            user_address_col = protocol_data.get('user_address_col', 'user_address')
            amount_col = protocol_data.get('amount_col', 'amount_usd')
            additional_where = protocol_data.get('additional_where', '')
            
            # Format additional WHERE if present
            if additional_where and not additional_where.strip().startswith('AND'):
                additional_where = f"AND {additional_where}"
            
            # Generate simplified UGS query
            query = f"""
            WITH monthly_active_addresses AS (
              SELECT
                DATE_TRUNC('month', {timestamp_col}) AS month,
                COUNT(DISTINCT {user_address_col}) AS active_addresses
              FROM {schema}.{user_table}
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
              FROM {schema}.{transaction_table}
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
            
            return query
    
    except Exception as e:
        logger.error(f"Error generating user growth query for {protocol}: {str(e)}")
        return f"""
        -- Fallback user growth query for {protocol} (error occurred during query generation)
        SELECT
            DATE_TRUNC('month', CURRENT_DATE) AS month,
            0 AS active_addresses,
            0 AS transaction_count,
            0 AS transaction_volume,
            0 AS active_address_growth_rate,
            0 AS transaction_count_growth_rate,
            0 AS transaction_volume_growth_rate,
            0 AS active_address_percentile,
            0 AS transaction_count_percentile,
            0 AS transaction_volume_percentile
        """