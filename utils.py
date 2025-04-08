import numpy as np
import logging

logger = logging.getLogger(__name__)

def normalize_score(value, min_val, max_val):
    """
    Normalize a value to a score between 0 and 1
    
    Parameters:
    value (float): The value to normalize
    min_val (float): The minimum expected value
    max_val (float): The maximum expected value
    
    Returns:
    float: Normalized score between 0 and 1
    """
    try:
        if max_val == min_val:
            return 0.5  # Default to middle if range is zero
        
        normalized = (value - min_val) / (max_val - min_val)
        return max(0, min(normalized, 1))  # Clamp between 0 and 1
    except Exception as e:
        logger.error(f"Error normalizing score: {str(e)}")
        return 0

def calculate_percentile_rank(values, target_value):
    """
    Calculate the percentile rank of a value within a list of values
    
    Parameters:
    values (list): List of values
    target_value (float): The value to find the percentile rank for
    
    Returns:
    float: Percentile rank between 0 and 1
    """
    try:
        if not values:
            return 0
        
        values = np.array(values)
        values = values[~np.isnan(values)]  # Remove NaN values
        
        if len(values) == 0:
            return 0
        
        # Count values less than target
        count_less = np.sum(values < target_value)
        count_equal = np.sum(values == target_value)
        
        # Use midpoint method for ranks
        percentile = (count_less + 0.5 * count_equal) / len(values)
        
        return percentile
    except Exception as e:
        logger.error(f"Error calculating percentile rank: {str(e)}")
        return 0

def format_large_number(num):
    """
    Format large numbers in a readable format (K, M, B)
    
    Parameters:
    num (float): The number to format
    
    Returns:
    str: Formatted number
    """
    try:
        if num is None:
            return "N/A"
        
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        else:
            return f"{num:.2f}"
    except Exception as e:
        logger.error(f"Error formatting large number: {str(e)}")
        return "Error"

def calculate_moving_average(values, window=3):
    """
    Calculate the moving average of a list of values
    
    Parameters:
    values (list): List of values
    window (int): Moving average window size
    
    Returns:
    list: Moving averages
    """
    try:
        if not values or window <= 0:
            return values
        
        values = np.array(values)
        moving_avgs = []
        
        for i in range(len(values)):
            start_idx = max(0, i - window + 1)
            window_vals = values[start_idx:i+1]
            moving_avgs.append(np.mean(window_vals))
        
        return moving_avgs
    except Exception as e:
        logger.error(f"Error calculating moving average: {str(e)}")
        return values
