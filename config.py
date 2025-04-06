import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro"  # Using Gemini 1.5 Pro model for best performance

# Data source URLs
DATA_SOURCES = {
    "data_gov_in": "https://data.gov.in/catalog/real-estate-properties-registration",
    "maharera": "https://maharera.mahaonline.gov.in/",
    "magicbricks": "https://www.magicbricks.com/",
    "housing_com": "https://housing.com/",
    "99acres": "https://www.99acres.com/",
    "square_yards": "https://www.squareyards.com/",
    # Government websites
    "delhi_land_records": "https://doris.delhi.gov.in/",
    "bangalore_city_corp": "https://www.bbmp.gov.in/",
    # Add more sources as needed
}

# Web scraping configuration
SCRAPING_CONFIG = {
    "cities": ["Mumbai", "Bangalore", "Delhi"],
    "max_pages_per_site": 5,
    "scraping_frequency_hours": 24,  # How often to update data
    "use_commercial_sites": True,
    "use_govt_sources": True,
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
}

# Path for storing data
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Cities for which we'll collect/generate data
CITIES = ["Mumbai", "Bangalore", "Delhi"]

# Maximum number of records to include in the LLM context
MAX_CONTEXT_RECORDS = 50

# Flask app settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
