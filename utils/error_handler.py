import os
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def safe_scraping(max_retries=3, backoff_factor=2):
    """
    Decorator for safe web scraping with retries and backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplicative factor for backoff between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Error during scraping: {str(e)}. Retry {retries+1}/{max_retries} in {wait_time}s")
                    time.sleep(wait_time)
                    retries += 1
            
            # If we've exhausted retries, log the error and return empty data
            logger.error(f"Failed after {max_retries} retries: {str(last_exception)}")
            return []  # Return empty list or appropriate default value
            
        return wrapper
    return decorator

def ensure_directory(file_path):
    """Ensure the directory exists before writing to a file"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def should_save_empty_results():
    """Check if empty results should be saved to files"""
    return os.getenv('SAVE_EMPTY_RESULTS', 'false').lower() == 'true'
