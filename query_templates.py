def get_revenue_query(protocol, months=12):
    """
    Generate a SQL query to fetch revenue data for a protocol from Dune Analytics
    
    Parameters:
    protocol (str): The name of the protocol (e.g. 'chainlink', 'uniswap')
    months (int): Number of months of historical data to fetch
    
    Returns:
    str: SQL query string
    """
    # Protocol-specific query templates
    if protocol.lower() == 'chainlink':
        return f"""
        WITH MonthlyFees AS (
          SELECT
            DATE_TRUNC('month', date_start) AS month,
            SUM(usd_amount) AS total_fees,
            'vrf' AS source
          FROM chainlink.vrf_reward_daily
          WHERE
            date_start >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
          UNION ALL
          SELECT
            DATE_TRUNC('month', date_start) AS month,
            SUM(usd_amount) AS total_fees,
            'automation' AS source
          FROM chainlink.automation_reward_daily
          WHERE
            date_start >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
          UNION ALL
          SELECT
            DATE_TRUNC('month', date_start) AS month,
            SUM(usd_amount) AS total_fees,
            'fm' AS source
          FROM chainlink.fm_reward_daily
          WHERE
            date_start >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
          UNION ALL
          SELECT
            DATE_TRUNC('month', date_start) AS month,
            SUM(usd_amount) AS total_fees,
            'ocr' AS source
          FROM chainlink.ocr_reward_daily
          WHERE
            date_start >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
          UNION ALL
          SELECT
            DATE_TRUNC('month', date_start) AS month,
            SUM(usd_amount) AS total_fees,
            'ccip' AS source
          FROM chainlink.ccip_reward_daily
          WHERE
            date_start >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
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
          month DESC,
          source
        """
    elif protocol.lower() == 'uniswap':
        return f"""
        WITH MonthlyFees AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            SUM(fee_usd) AS total_fees,
            version AS source
          FROM (
            SELECT 
              block_time,
              fee_usd,
              'v2' as version
            FROM uniswap_v2.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              fee_usd,
              'v3' as version
            FROM uniswap_v3.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_trades
          GROUP BY 1, 3
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
          month DESC,
          source
        """
    elif protocol.lower() == 'aave':
        return f"""
        WITH MonthlyFees AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            SUM(interest_usd) AS total_fees,
            version AS source
          FROM (
            SELECT 
              block_time,
              interest_usd,
              'v2' as version
            FROM aave_v2.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              interest_usd,
              'v3' as version
            FROM aave_v3.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_borrows
          GROUP BY 1, 3
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
          month DESC,
          source
        """
    else:
        # Generic template for other protocols
        # This would need to be customized based on available tables for each protocol
        return f"""
        WITH MonthlyFees AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            SUM(fee_usd) AS total_fees,
            'total' AS source
          FROM {protocol}.trades
          WHERE
            block_time >= CURRENT_DATE - INTERVAL '{months}' month
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
          month DESC,
          source
        """

def get_user_growth_query(protocol, months=12):
    """
    Generate a SQL query to fetch user growth data for a protocol from Dune Analytics
    
    Parameters:
    protocol (str): The name of the protocol (e.g. 'chainlink', 'uniswap')
    months (int): Number of months of historical data to fetch
    
    Returns:
    str: SQL query string
    """
    # Protocol-specific query templates
    if protocol.lower() == 'chainlink':
        return f"""
        WITH monthly_active_addresses AS (
          SELECT
            DATE_TRUNC('month', evt_block_time) AS month,
            COUNT(DISTINCT evt_tx_from) AS active_addresses
          FROM (
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_ethereum.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_avalanche_c.bridgetoken_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_fantom.chainlink_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_ronin.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_optimism.linktokenoptimism_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_multichain.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_tx_from,
              evt_block_time
            FROM chainlink_polygon.linktoken_evt_transfer
          ) AS transfers
          WHERE
            evt_block_time >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
        ), transaction_count_volume AS (
          SELECT
            DATE_TRUNC('month', evt_block_time) AS month,
            COUNT(*) AS transaction_count,
            SUM(value) AS transaction_volume
          FROM (
            SELECT
              evt_block_time,
              value
            FROM chainlink_ethereum.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_avalanche_c.bridgetoken_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_fantom.chainlink_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_ronin.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_optimism.linktokenoptimism_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_multichain.linktoken_evt_transfer
            UNION ALL
            SELECT
              evt_block_time,
              value
            FROM chainlink_polygon.linktoken_evt_transfer
          ) AS transfers
          WHERE
            evt_block_time >= CURRENT_DATE - INTERVAL '{months}' month
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
        )
        SELECT
          month,
          active_addresses,
          transaction_count,
          transaction_volume,
          active_address_growth_rate,
          transaction_count_growth_rate,
          transaction_volume_growth_rate
        FROM growth_rates
        ORDER BY
          month DESC
        """
    elif protocol.lower() == 'uniswap':
        return f"""
        WITH monthly_active_addresses AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(DISTINCT taker) AS active_addresses
          FROM (
            SELECT 
              block_time,
              taker
            FROM uniswap_v2.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              taker
            FROM uniswap_v3.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_trades
          GROUP BY
            1
        ), transaction_count_volume AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(*) AS transaction_count,
            SUM(amount_usd) AS transaction_volume
          FROM (
            SELECT 
              block_time,
              amount_usd
            FROM uniswap_v2.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM uniswap_v3.trades
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_trades
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
        )
        SELECT
          month,
          active_addresses,
          transaction_count,
          transaction_volume,
          active_address_growth_rate,
          transaction_count_growth_rate,
          transaction_volume_growth_rate
        FROM growth_rates
        ORDER BY
          month DESC
        """
    elif protocol.lower() == 'aave':
        return f"""
        WITH monthly_active_addresses AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(DISTINCT user) AS active_addresses
          FROM (
            SELECT 
              block_time,
              user
            FROM aave_v2.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v2.deposit
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v2.repay
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v2.withdraw
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v3.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v3.deposit
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v3.repay
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              user
            FROM aave_v3.withdraw
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_actions
          GROUP BY
            1
        ), transaction_count_volume AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(*) AS transaction_count,
            SUM(COALESCE(amount_usd, 0)) AS transaction_volume
          FROM (
            SELECT 
              block_time,
              amount_usd
            FROM aave_v2.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v2.deposit
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v2.repay
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v2.withdraw
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v3.borrow
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v3.deposit
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v3.repay
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
            UNION ALL
            SELECT 
              block_time,
              amount_usd
            FROM aave_v3.withdraw
            WHERE
              block_time >= CURRENT_DATE - INTERVAL '{months}' month
          ) AS combined_actions
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
        )
        SELECT
          month,
          active_addresses,
          transaction_count,
          transaction_volume,
          active_address_growth_rate,
          transaction_count_growth_rate,
          transaction_volume_growth_rate
        FROM growth_rates
        ORDER BY
          month DESC
        """
    else:
        # Generic template for other protocols
        # This would need to be customized based on available tables for each protocol
        return f"""
        WITH monthly_active_addresses AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(DISTINCT user_address) AS active_addresses
          FROM {protocol}.trades
          WHERE
            block_time >= CURRENT_DATE - INTERVAL '{months}' month
          GROUP BY
            1
        ), transaction_count_volume AS (
          SELECT
            DATE_TRUNC('month', block_time) AS month,
            COUNT(*) AS transaction_count,
            SUM(amount_usd) AS transaction_volume
          FROM {protocol}.trades
          WHERE
            block_time >= CURRENT_DATE - INTERVAL '{months}' month
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
        )
        SELECT
          month,
          active_addresses,
          transaction_count,
          transaction_volume,
          active_address_growth_rate,
          transaction_count_growth_rate,
          transaction_volume_growth_rate
        FROM growth_rates
        ORDER BY
          month DESC
        """
