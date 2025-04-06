import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
import time
import random
import json
import re
from datetime import datetime
from urllib.parse import urljoin
from config import DATA_DIR, DATA_SOURCES, SCRAPING_CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealEstateDataScraper:
    def __init__(self):
        self.data_dir = DATA_DIR
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Ensure city subdirectories exist
        for city in SCRAPING_CONFIG['cities']:
            city_dir = os.path.join(self.data_dir, city.lower())
            os.makedirs(city_dir, exist_ok=True)
    
    def scrape_magicbricks(self, city, property_type="all", max_pages=3):
        """
        Scrape real estate data from Magicbricks website
        
        Args:
            city (str): City name
            property_type (str): Type of property (all, buy, rent)
            max_pages (int): Maximum number of pages to scrape
        """
        try:
            city_formatted = city.lower().replace(" ", "-")
            base_url = f"https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa,Residential-Plot&cityName={city_formatted}"
            
            logger.info(f"Scraping Magicbricks for {city}, property type: {property_type}")
            
            all_properties = []
            
            for page in range(1, max_pages + 1):
                page_url = f"{base_url}&page={page}"
                logger.info(f"Scraping page {page} - {page_url}")
                
                try:
                    # Add random delay to avoid being blocked
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
                    
                    response = requests.get(page_url, headers=self.headers)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract property listings
                    property_cards = soup.select('.mb-srp__card')
                    
                    if not property_cards:
                        logger.warning(f"No property cards found on page {page}")
                        break
                    
                    for card in property_cards:
                        try:
                            property_data = self._parse_magicbricks_card(card, city)
                            if property_data:
                                all_properties.append(property_data)
                        except Exception as e:
                            logger.error(f"Error parsing property card: {str(e)}")
                            continue
                    
                    logger.info(f"Extracted {len(property_cards)} properties from page {page}")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching page {page}: {str(e)}")
                    break
            
            # Convert to DataFrame and save
            if all_properties:
                df = pd.DataFrame(all_properties)
                self._save_property_data(df, city, source="magicbricks")
                return df
            else:
                logger.warning(f"No properties extracted for {city}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping Magicbricks for {city}: {str(e)}")
            return None
    
    def _parse_magicbricks_card(self, card, city):
        """Parse a single property card from Magicbricks"""
        try:
            # Extract price
            price_elem = card.select_one('.mb-srp__card__price')
            price_text = price_elem.text.strip() if price_elem else "N/A"
            
            # Convert price to lakhs
            price_lakhs = self._extract_price_in_lakhs(price_text)
            
            # Extract area
            area_elem = card.select_one('.mb-srp__card__summary--value')
            area_text = area_elem.text.strip() if area_elem else "N/A"
            area_sqft = self._extract_area_sqft(area_text)
            
            # Extract locality
            locality_elem = card.select_one('.mb-srp__card__society')
            locality = locality_elem.text.strip() if locality_elem else "N/A"
            
            # Extract property type
            property_type_elem = card.select_one('.mb-srp__card__desc--text')
            property_type = property_type_elem.text.strip() if property_type_elem else "Flat"
            
            # Extract bedrooms (BHK)
            bhk_elem = card.select_one('.mb-srp__card__config .mb-srp__card__config--value')
            bedrooms = self._extract_bhk(bhk_elem.text.strip() if bhk_elem else "N/A")
            
            # Calculate price per sqft
            price_per_sqft = round(price_lakhs * 100000 / area_sqft) if area_sqft > 0 and price_lakhs > 0 else 0
            
            return {
                'city': city,
                'locality': locality,
                'property_type': 'Flat' if 'apartment' in property_type.lower() else property_type,
                'bedrooms': bedrooms,
                'area_sqft': area_sqft,
                'price_per_sqft': price_per_sqft,
                'price_total': price_lakhs,
                'transaction_date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'magicbricks'
            }
            
        except Exception as e:
            logger.error(f"Error parsing Magicbricks card: {str(e)}")
            return None
    
    def scrape_housing_com(self, city, property_type="buy", max_pages=3):
        """
        Scrape real estate data from Housing.com website
        
        Args:
            city (str): City name
            property_type (str): Type of property (buy, rent)
            max_pages (int): Maximum number of pages to scrape
        """
        try:
            city_formatted = city.lower().replace(" ", "-")
            base_url = f"https://housing.com/{property_type}-real-estate-{city_formatted}"
            
            logger.info(f"Scraping Housing.com for {city}, property type: {property_type}")
            
            all_properties = []
            
            for page in range(1, max_pages + 1):
                page_url = f"{base_url}/p{page}"
                logger.info(f"Scraping page {page} - {page_url}")
                
                try:
                    # Add random delay to avoid being blocked
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                    
                    response = requests.get(page_url, headers=self.headers)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract property listings
                    property_cards = soup.select('.css-1nr7r9e')
                    
                    if not property_cards:
                        logger.warning(f"No property cards found on page {page}")
                        break
                    
                    for card in property_cards:
                        try:
                            property_data = self._parse_housing_card(card, city)
                            if property_data:
                                all_properties.append(property_data)
                        except Exception as e:
                            logger.error(f"Error parsing property card: {str(e)}")
                            continue
                    
                    logger.info(f"Extracted {len(property_cards)} properties from page {page}")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching page {page}: {str(e)}")
                    break
            
            # Convert to DataFrame and save
            if all_properties:
                df = pd.DataFrame(all_properties)
                self._save_property_data(df, city, source="housing_com")
                return df
            else:
                logger.warning(f"No properties extracted for {city}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping Housing.com for {city}: {str(e)}")
            return None
    
    def _parse_housing_card(self, card, city):
        """Parse a single property card from Housing.com"""
        try:
            # Implementation would be similar to magicbricks parser but adapted for housing.com HTML structure
            # This is a placeholder - real implementation would need to inspect the actual HTML structure
            
            # For demonstration, assuming similar structure to magicbricks
            price_elem = card.select_one('.css-19z8mym')
            price_text = price_elem.text.strip() if price_elem else "N/A"
            price_lakhs = self._extract_price_in_lakhs(price_text)
            
            area_elem = card.select_one('.css-1h6hiy6')
            area_text = area_elem.text.strip() if area_elem else "N/A"
            area_sqft = self._extract_area_sqft(area_text)
            
            locality_elem = card.select_one('.css-1k3en0k')
            locality = locality_elem.text.strip() if locality_elem else "N/A"
            
            bhk_elem = card.select_one('.css-1s2jtz8')
            bedrooms = self._extract_bhk(bhk_elem.text.strip() if bhk_elem else "N/A")
            
            # Calculate price per sqft
            price_per_sqft = round(price_lakhs * 100000 / area_sqft) if area_sqft > 0 and price_lakhs > 0 else 0
            
            return {
                'city': city,
                'locality': locality,
                'property_type': 'Flat',
                'bedrooms': bedrooms,
                'area_sqft': area_sqft,
                'price_per_sqft': price_per_sqft,
                'price_total': price_lakhs,
                'transaction_date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'housing_com'
            }
            
        except Exception as e:
            logger.error(f"Error parsing Housing.com card: {str(e)}")
            return None
    
    def scrape_govt_data(self, city):
        """
        Scrape real estate data from government websites
        
        Args:
            city (str): City name
        """
        # Implementation would depend on the specific government website structure
        # This is a placeholder - the real implementation would need to be adapted for each site
        
        try:
            if city.lower() == "mumbai":
                return self._scrape_maharera()
            elif city.lower() == "delhi":
                return self._scrape_delhi_govt_data()
            elif city.lower() == "bangalore":
                return self._scrape_bangalore_govt_data()
            else:
                logger.warning(f"No government data scraper implemented for {city}")
                return None
        except Exception as e:
            logger.error(f"Error scraping government data for {city}: {str(e)}")
            return None
    
    def _scrape_maharera(self):
        """Scrape data from Maharashtra RERA website"""
        try:
            url = DATA_SOURCES["maharera"]
            logger.info(f"Scraping data from {url}")
            
            # Placeholder for actual implementation
            logger.info("Maharashtra RERA scraping would be implemented here based on website structure")
            
            # For demo, use dummy data generator - updated to 1500 records
            from data_generator import generate_city_data
            df = generate_city_data("Mumbai", num_records=1500)
            df['source'] = 'maharera'
            self._save_property_data(df, "Mumbai", source="maharera")
            
            return df
        except Exception as e:
            logger.error(f"Error scraping Maharashtra RERA website: {str(e)}")
            return None
    
    def _scrape_delhi_govt_data(self):
        """Scrape data from Delhi government websites"""
        # Implementation placeholder - updated to 1500 records
        from data_generator import generate_city_data
        df = generate_city_data("Delhi", num_records=1500)
        df['source'] = 'delhi_govt'
        self._save_property_data(df, "Delhi", source="delhi_govt")
        return df
    
    def _scrape_bangalore_govt_data(self):
        """Scrape data from Bangalore government websites"""
        # Implementation placeholder - updated to 1500 records
        from data_generator import generate_city_data
        df = generate_city_data("Bangalore", num_records=1500)
        df['source'] = 'bangalore_govt'
        self._save_property_data(df, "Bangalore", source="bangalore_govt")
        return df
    
    def _extract_price_in_lakhs(self, price_text):
        """Extract price in lakhs from price text"""
        try:
            # Remove all non-numeric characters except decimal point
            price_text = price_text.lower()
            
            # Handle different formats
            if 'cr' in price_text or 'crore' in price_text:
                # Convert crore to lakhs
                num = re.search(r'(\d+\.?\d*)', price_text).group(1)
                return float(num) * 100  # 1 crore = 100 lakhs
            elif 'lac' in price_text or 'lakh' in price_text:
                num = re.search(r'(\d+\.?\d*)', price_text).group(1)
                return float(num)
            else:
                # Assuming price in thousands or raw amount
                num = re.search(r'(\d+\.?\d*)', price_text).group(1)
                val = float(num)
                
                # Convert to lakhs if necessary
                if val > 10000:  # Likely in raw rupees
                    return val / 100000
                else:  # Likely in thousands
                    return val / 100
                
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)} from '{price_text}'")
            return 0
    
    def _extract_area_sqft(self, area_text):
        """Extract area in square feet from area text"""
        try:
            # Extract numeric value
            area_match = re.search(r'(\d+\.?\d*)', area_text)
            if not area_match:
                return 0
                
            area_val = float(area_match.group(1))
            
            # Check for unit
            if 'sq.m' in area_text.lower() or 'sqm' in area_text.lower():
                # Convert square meters to square feet
                return area_val * 10.764
            else:
                # Assume square feet
                return area_val
                
        except Exception as e:
            logger.error(f"Error extracting area: {str(e)} from '{area_text}'")
            return 0
    
    def _extract_bhk(self, bhk_text):
        """Extract number of bedrooms from BHK text"""
        try:
            # Look for patterns like "2 BHK", "3BHK", etc.
            bhk_match = re.search(r'(\d+)\s*bhk', bhk_text.lower())
            if bhk_match:
                return int(bhk_match.group(1))
                
            # Try to find just a number
            num_match = re.search(r'(\d+)', bhk_text)
            if num_match:
                return int(num_match.group(1))
                
            return 1  # Default to 1 if can't extract
            
        except Exception as e:
            logger.error(f"Error extracting BHK: {str(e)} from '{bhk_text}'")
            return 1
    
    def _save_property_data(self, df, city, source):
        """Save property data to CSV"""
        try:
            # Clean the data
            df = self.clean_data(df)
            
            # Create city directory if it doesn't exist
            city_dir = os.path.join(self.data_dir, city.lower())
            os.makedirs(city_dir, exist_ok=True)
            
            # Save to CSV with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(city_dir, f"{source}_{timestamp}.csv")
            df.to_csv(file_path, index=False)
            
            # Also save to the consolidated file
            consolidated_file = os.path.join(self.data_dir, f"{city.lower()}.csv")
            
            if os.path.exists(consolidated_file):
                existing_df = pd.read_csv(consolidated_file)
                combined_df = pd.concat([existing_df, df]).drop_duplicates(subset=['locality', 'property_type', 'bedrooms', 'area_sqft', 'price_total'])
                combined_df.to_csv(consolidated_file, index=False)
            else:
                df.to_csv(consolidated_file, index=False)
                
            logger.info(f"Data saved to {file_path} and consolidated to {consolidated_file}")
            
        except Exception as e:
            logger.error(f"Error saving property data: {str(e)}")
    
    def clean_data(self, df):
        """
        Clean and preprocess the scraped data
        
        Args:
            df (pd.DataFrame): Raw dataframe
            
        Returns:
            pd.DataFrame: Cleaned dataframe
        """
        try:
            # Remove duplicates
            df = df.drop_duplicates()
            
            # Handle missing values
            df = df.dropna(subset=["price_total", "area_sqft"])  # Drop rows without price or area
            
            # Filter out outliers (example: properties with unrealistically high or low prices)
            if len(df) > 10:  # Only apply if we have enough data
                df = df[(df["price_per_sqft"] > 1000) & (df["price_per_sqft"] < 100000)]
            
            # Convert data types
            if "transaction_date" in df.columns:
                df["transaction_date"] = pd.to_datetime(df["transaction_date"])
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning data: {str(e)}")
            return df
    
    def run_scraping(self, cities=None):
        """
        Run all scraping methods for specified cities
        
        Args:
            cities (list): List of cities to scrape. If None, uses cities from config
        """
        if cities is None:
            cities = SCRAPING_CONFIG['cities']
        
        for city in cities:
            logger.info(f"=============== Scraping data for {city} ===============")
            
            # Scrape from commercial websites
            if SCRAPING_CONFIG.get('use_commercial_sites', True):
                logger.info(f"Scraping commercial websites for {city}")
                self.scrape_magicbricks(city, max_pages=SCRAPING_CONFIG.get('max_pages_per_site', 3))
                self.scrape_housing_com(city, max_pages=SCRAPING_CONFIG.get('max_pages_per_site', 3))
            
            # Scrape from government sources
            if SCRAPING_CONFIG.get('use_govt_sources', True):
                logger.info(f"Scraping government sources for {city}")
                self.scrape_govt_data(city)
            
            logger.info(f"Completed scraping for {city}")
        
        logger.info("All scraping tasks completed")

# Function to run scraping as a background task
def run_background_scraping():
    """Run scraping in background"""
    scraper = RealEstateDataScraper()
    scraper.run_scraping()

if __name__ == "__main__":
    scraper = RealEstateDataScraper()
    scraper.run_scraping()
