import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Common headers to mimic a browser
USER_AGENTS = [
    os.getenv('USER_AGENT'),
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
]

def get_request_headers():
    """Generate headers for HTTP requests to avoid detection"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def get_housing_url(city, page=1):
    """Generate the correct URL format for Housing.com"""
    url_format = os.getenv('HOUSING_URL_FORMAT', 
                          'https://housing.com/in/buy/search-real-estate-to-buy-in-{city}?page={page}')
    return url_format.format(city=city.lower(), page=page)

def get_magicbricks_url(city, page=1):
    """Generate the correct URL format for Magicbricks"""
    url_format = os.getenv('MAGICBRICKS_URL_FORMAT')
    return url_format.format(city=city.lower(), page=page)

def get_request_timeout():
    """Get request timeout from environment variable or use default"""
    return int(os.getenv('REQUEST_TIMEOUT', 30))

def get_request_delay():
    """Get delay between requests to avoid rate limiting"""
    delay = float(os.getenv('REQUEST_DELAY', 2))
    # Add some randomization to seem more human-like
    return delay + random.uniform(0.5, 1.5)

def is_scraper_enabled(scraper_name):
    """Check if a specific scraper is enabled in environment variables"""
    env_var = f'ENABLE_{scraper_name.upper()}'
    return os.getenv(env_var, 'true').lower() == 'true'
