import argparse
import json
import os
import threading
import time
import schedule
import logging
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template, Response
from llm_predictor import LLMRealEstatePricePredictor
from scraper import RealEstateDataScraper, run_background_scraping
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, CITIES, DATA_DIR, SCRAPING_CONFIG
from dotenv import load_dotenv
from utils.scraper_config import (
    get_request_headers, get_housing_url, get_magicbricks_url,
    get_request_timeout, get_request_delay, is_scraper_enabled
)
from utils.error_handler import safe_scraping, ensure_directory, should_save_empty_results

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize predictor
predictor = LLMRealEstatePricePredictor()

# Flask app
app = Flask(__name__)

# Schedule for periodic data refresh
def schedule_scraping():
    """Schedule periodic scraping based on configuration"""
    frequency_hours = SCRAPING_CONFIG.get('scraping_frequency_hours', 24)
    schedule.every(frequency_hours).hours.do(run_background_scraping)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', cities=CITIES)

@app.route('/predict', methods=['POST'])
def predict():
    """API endpoint for price prediction"""
    data = request.json
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    result = predictor.predict_price(user_query)
    return jsonify(result)

@app.route('/cli_predict', methods=['POST'])
def cli_predict():
    """API endpoint for CLI mode prediction - formatted for terminal output"""
    data = request.json
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    result = predictor.predict_price(user_query)
    
    # Format the result for CLI display
    response = {
        "formatted_output": format_prediction_for_cli(result),
        "raw_result": result
    }
    
    return jsonify(response)

@app.route('/query', methods=['POST'])
def query():
    """API endpoint for any real estate query"""
    data = request.json
    user_query = data.get('query', '')
    
    if not user_query:
        return jsonify({"error": "No query provided"}), 400
    
    result = predictor.answer_query(user_query)
    return jsonify(result)

@app.route('/refresh_data', methods=['POST'])
def refresh_data():
    """API endpoint to trigger data refresh"""
    data = request.json
    cities = data.get('cities', CITIES)
    
    if not cities:
        return jsonify({"error": "No cities specified"}), 400
    
    # Start scraping in a background thread
    thread = threading.Thread(target=lambda: RealEstateDataScraper().run_scraping(cities))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": f"Data refresh initiated for: {', '.join(cities)}",
        "status": "processing"
    })

@app.route('/data_status', methods=['GET'])
def data_status():
    """API endpoint to check data freshness"""
    city = request.args.get('city', '')
    
    if not city:
        return jsonify({"error": "No city specified"}), 400
    
    # Check if city data exists
    city_path = os.path.join(DATA_DIR, f"{city.lower()}.csv")
    if not os.path.exists(city_path):
        return jsonify({
            "city": city,
            "status": "no_data",
            "message": f"No data available for {city}"
        })
    
    # Get file modification time
    mod_time = os.path.getmtime(city_path)
    mod_date = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculate age in hours
    age_hours = (datetime.datetime.now().timestamp() - mod_time) / 3600
    
    return jsonify({
        "city": city,
        "status": "available",
        "last_updated": mod_date,
        "age_hours": round(age_hours, 1),
        "is_fresh": age_hours < SCRAPING_CONFIG.get('scraping_frequency_hours', 24)
    })

@safe_scraping(max_retries=3, backoff_factor=2)
def scrape_magicbricks(city, page=1):
    """Scrape property data from Magicbricks with improved error handling"""
    if not is_scraper_enabled('MAGICBRICKS'):
        logger.info(f"Magicbricks scraper is disabled. Skipping for {city}")
        return []
    
    url = get_magicbricks_url(city, page)
    logger.info(f"Scraping page {page} - {url}")
    
    # Add delay to avoid rate limiting
    time.sleep(get_request_delay())
    
    response = requests.get(url, headers=get_request_headers(), timeout=get_request_timeout())
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    property_cards = soup.select('div.mb-srp__card')
    
    if not property_cards:
        logger.warning(f"No property cards found on page {page}")
        return []
        
    # Continue with your existing extraction logic
    # ... existing property extraction code ...
    
    return extracted_properties

@safe_scraping(max_retries=3, backoff_factor=2)
def scrape_housing(city, page=1):
    """Scrape property data from Housing.com with updated URLs and error handling"""
    if not is_scraper_enabled('HOUSING'):
        logger.info(f"Housing.com scraper is disabled. Skipping for {city}")
        return []
    
    url = get_housing_url(city, page)
    logger.info(f"Scraping page {page} - {url}")
    
    # Add delay to avoid rate limiting
    time.sleep(get_request_delay())
    
    response = requests.get(url, headers=get_request_headers(), timeout=get_request_timeout())
    response.raise_for_status()
    
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Update the selector based on Housing.com's current HTML structure
    # You may need to inspect the actual website to get the correct selectors
    property_cards = soup.select('article.css-1nr7r9e')
    
    if not property_cards:
        logger.warning(f"No property cards found on page {page}")
        return []
    
    # Continue with your existing extraction logic
    # ... existing property extraction code ...
    
    return extracted_properties

def save_properties_to_file(properties, city, source):
    """Save scraped properties to CSV file with proper directory handling"""
    if not properties and not should_save_empty_results():
        logger.info(f"No properties to save for {city} from {source}")
        return None
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    city_dir = f"data/{city.lower()}"
    
    # Ensure directory exists
    ensure_directory(city_dir)
    
    # Save the individual source file
    source_file = f"{city_dir}/{source}_{timestamp}.csv"
    
    df = pd.DataFrame(properties)
    df.to_csv(source_file, index=False)
    
    # Update consolidated file
    consolidated_file = f"data/{city.lower()}.csv"
    
    if os.path.exists(consolidated_file):
        consolidated_df = pd.read_csv(consolidated_file)
        consolidated_df = pd.concat([consolidated_df, df], ignore_index=True)
    else:
        consolidated_df = df
    
    consolidated_df.to_csv(consolidated_file, index=False)
    
    logger.info(f"Data saved to {source_file} and consolidated to {consolidated_file}")
    
    return source_file

def scrape_city_data(city):
    """Scrape data for a specific city with improved error handling"""
    logger.info(f"=============== Scraping data for {city} ===============")
    
    # Scrape commercial websites
    logger.info(f"Scraping commercial websites for {city}")
    
    # Scrape Magicbricks
    properties_mb = []
    if is_scraper_enabled('MAGICBRICKS'):
        logger.info(f"Scraping Magicbricks for {city}, property type: all")
        try:
            properties_mb = scrape_magicbricks(city)
            if properties_mb:
                save_properties_to_file(properties_mb, city, "magicbricks")
            else:
                logger.warning(f"No properties extracted for {city}")
        except Exception as e:
            logger.error(f"Error scraping Magicbricks for {city}: {str(e)}")
    
    # Scrape Housing.com
    properties_housing = []
    if is_scraper_enabled('HOUSING'):
        logger.info(f"Scraping Housing.com for {city}, property type: buy")
        try:
            properties_housing = scrape_housing(city)
            if properties_housing:
                save_properties_to_file(properties_housing, city, "housing")
            else:
                logger.warning(f"No properties extracted for {city}")
        except Exception as e:
            logger.error(f"Error scraping Housing.com for {city}: {str(e)}")
    
    # Scrape government sources
    if is_scraper_enabled('GOVERNMENT'):
        logger.info(f"Scraping government sources for {city}")
        
        # Existing government scraping logic, wrapped in try-except
        try:
            # ... existing government scraping code ...
            
            # Example for Maharashtra RERA
            if city.lower() == "mumbai":
                logger.info("Scraping data from https://maharera.mahaonline.gov.in/")
                logger.info("Maharashtra RERA scraping would be implemented here based on website structure")
                
                # Mock data for example - updated to 1500 records
                govt_data = [{"property_id": f"{city}_govt_{i}", "source": "govt"} for i in range(1500)]
                save_properties_to_file(govt_data, city, f"{city.lower()}_govt")
        except Exception as e:
            logger.error(f"Error scraping government sources for {city}: {str(e)}")
    
    logger.info(f"Completed scraping for {city}")

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start scraping process for specified cities"""
    data = request.get_json()
    cities = data.get('cities', ['Mumbai', 'Bangalore', 'Delhi'])
    
    for city in cities:
        scrape_city_data(city)
    
    logger.info("All scraping tasks completed")
    return jsonify({"status": "success", "message": "Scraping completed"})

def format_prediction_for_cli(prediction):
    """Format the prediction result for CLI display"""
    if "error" in prediction:
        return f"Error: {prediction['error']}"
    
    query_type = prediction.get("query_type", "price_prediction")
    
    output = "\n" + "="*50 + "\n"
    output += "REAL ESTATE QUERY RESPONSE\n"
    output += "="*50 + "\n\n"
    
    if query_type == "price_prediction":
        output += f"🏠 Predicted Price: ₹{prediction.get('predicted_price_lakhs', 'N/A')} lakhs\n"
        output += f"🔄 Price Range: {prediction.get('predicted_price_range', 'N/A')}\n\n"
        output += "💡 Explanation:\n"
        output += f"{prediction.get('explanation', 'No explanation provided.')}\n"
    
    elif query_type == "market_trend":
        output += f"📈 Market Direction: {prediction.get('market_direction', 'N/A')}\n"
        output += f"🔄 Expected Annual Growth: {prediction.get('expected_annual_growth_percent', 'N/A')}%\n\n"
        output += "💡 Analysis:\n"
        output += f"{prediction.get('analysis', 'No analysis provided.')}\n"
    
    elif query_type == "comparison":
        output += "📊 Comparison:\n"
        output += f"{prediction.get('comparison_table', 'No comparison data available.')}\n\n"
        output += f"🏆 Recommendation: {prediction.get('recommendation', 'N/A')}\n\n"
        output += "💡 Reasoning:\n"
        output += f"{prediction.get('reasoning', 'No reasoning provided.')}\n"
    
    elif query_type == "investment_advice":
        output += f"💰 Investment Recommendation: {prediction.get('investment_recommendation', 'N/A')}\n"
        output += f"📈 Projected Annual ROI: {prediction.get('projected_annual_roi_percent', 'N/A')}%\n\n"
        output += "💡 Investment Analysis:\n"
        output += f"{prediction.get('investment_analysis', 'No analysis provided.')}\n"
    
    elif query_type == "regulation":
        output += "⚖️ Legal Information:\n"
        output += f"{prediction.get('legal_information', 'No legal information available.')}\n\n"
        output += "📋 Practical Steps:\n"
        output += f"{prediction.get('practical_steps', 'No practical steps provided.')}\n\n"
    
    else:  # general
        output += "💡 Answer:\n"
        output += f"{prediction.get('answer', 'No answer provided.')}\n\n"
    
    output += "\n" + "="*50
    return output

def create_flask_app():
    """Create and configure Flask app"""
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create an enhanced HTML template for the real estate AI app
    with open('templates/index.html', 'w') as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Real Estate Insights - AI-Powered Analysis</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 20px;
            line-height: 1.6;
        }
        .container { 
            border: 1px solid #ccc; 
            border-radius: 8px; 
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .result { 
            margin-top: 20px; 
            padding: 20px; 
            border-left: 4px solid #4CAF50; 
            background-color: #f9f9f9; 
            display: none;
            border-radius: 5px;
        }
        button { 
            background-color: #4CAF50; 
            color: white; 
            padding: 10px 18px; 
            border: none; 
            border-radius: 4px; 
            cursor: pointer; 
            font-size: 16px;
            transition: background-color 0.3s;
        }
        button:hover { 
            background-color: #45a049; 
        }
        select, textarea { 
            width: 100%; 
            padding: 12px; 
            margin: 8px 0; 
            display: inline-block; 
            border: 1px solid #ccc; 
            border-radius: 4px; 
            box-sizing: border-box; 
            font-size: 16px;
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 2s linear infinite;
            display: none;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .examples {
            margin: 20px 0;
            padding: 15px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        .example-query {
            cursor: pointer;
            color: #0066cc;
            margin-bottom: 8px;
            padding: 5px;
            transition: background-color 0.2s;
        }
        .example-query:hover {
            background-color: #e6f2ff;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            margin-right: 5px;
            border-radius: 5px 5px 0 0;
        }
        .tab.active {
            background-color: #4CAF50;
            color: white;
            border-bottom: none;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .data-status {
            display: flex;
            justify-content: space-between;
            background-color: #e8f4fe;
            padding: 10px 15px;
            border-radius: 4px;
            margin: 15px 0;
            font-size: 14px;
        }
        .data-status-fresh {
            color: green;
        }
        .data-status-stale {
            color: orange;
        }
        .query-type-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
            background-color: #eee;
            color: #333;
        }
        .refresh-button {
            background-color: #3498db;
            margin-left: 10px;
        }
        .refresh-button:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <h1>Real Estate Insights - AI-Powered Analysis</h1>
    
    <div class="tabs">
        <div class="tab active" data-tab="query">Ask a Question</div>
        <div class="tab" data-tab="data">Data Status</div>
        <div class="tab" data-tab="about">About</div>
    </div>
    
    <div class="tab-content active" id="query-tab">
        <div class="container">
            <h3>Ask anything about real estate in India</h3>
            
            <div class="data-status" id="query-data-status">
                <span>Checking data status...</span>
            </div>
            
            <label for="query">Your Question:</label>
            <textarea id="query" rows="4" placeholder="Example: Estimate the price of a 3 BHK apartment in Koramangala, Bangalore with 1500 sq.ft area."></textarea>
            
            <div class="examples">
                <h4>Example Questions:</h4>
                <div class="example-query" onclick="useExample(this.innerText)">Estimate the price of a 3 BHK apartment in Koramangala, Bangalore with 1500 sq.ft area.</div>
                <div class="example-query" onclick="useExample(this.innerText)">What would a 2 BHK flat in Andheri, Mumbai cost if it's around 950 sq.ft?</div>
                <div class="example-query" onclick="useExample(this.innerText)">What's the price trend for properties in Vasant Kunj, Delhi over the last year?</div>
                <div class="example-query" onclick="useExample(this.innerText)">Compare investment potential between Whitefield and HSR Layout in Bangalore.</div>
                <div class="example-query" onclick="useExample(this.innerText)">What are the stamp duty charges for property registration in Delhi?</div>
                <div class="example-query" onclick="useExample(this.innerText)">Is it a good time to invest in a 2 BHK flat in Bandra, Mumbai?</div>
            </div>
            
            <button onclick="getAnswer()">Get Insights</button>
            
            <div id="loader" class="loader"></div>
            
            <div id="result" class="result">
                <h3>Analysis Result <span id="query-type-badge" class="query-type-badge">Price Prediction</span></h3>
                
                <!-- Dynamic result sections will appear based on query type -->
                <div id="result-content"></div>
            </div>
        </div>
    </div>
    
    <div class="tab-content" id="data-tab">
        <div class="container">
            <h3>Real Estate Data Status</h3>
            <p>Here you can check the freshness of the data and trigger data updates.</p>
            
            <div id="data-status-container">
                <!-- Data status for each city will be displayed here -->
                <div class="data-status">Loading data status...</div>
            </div>
            
            <button onclick="refreshAllData()" class="refresh-button">Refresh All Data</button>
            <div id="refresh-status"></div>
        </div>
    </div>
    
    <div class="tab-content" id="about-tab">
        <div class="container">
            <h3>About This Project</h3>
            <p>This application uses real-time data from property websites and government sources to provide AI-powered insights about the Indian real estate market.</p>
            
            <h4>Features:</h4>
            <ul>
                <li>Real-time property price prediction</li>
                <li>Market trend analysis</li>
                <li>Property comparison</li>
                <li>Investment advice</li>
                <li>Regulatory information</li>
            </ul>
            
            <h4>Data Sources:</h4>
            <p>We collect data from multiple sources including:</p>
            <ul>
                <li>Commercial property websites (MagicBricks, Housing.com, etc.)</li>
                <li>Government property registration data</li>
                <li>Historical transaction records</li>
            </ul>
            
            <h4>How it works:</h4>
            <p>Our system collects and analyzes real-time property data, which is then processed by an advanced AI model to provide accurate insights and predictions.</p>
        </div>
    </div>

    <script>
        // Tab functionality
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                this.classList.add('active');
                document.getElementById(this.getAttribute('data-tab') + '-tab').classList.add('active');
                
                // If data tab is selected, load data status
                if (this.getAttribute('data-tab') === 'data') {
                    loadAllDataStatus();
                }
            });
        });
        
        // Load data status on page load
        window.addEventListener('load', function() {
            checkDataStatus('Mumbai');
            checkDataStatus('Bangalore');
            checkDataStatus('Delhi');
        });
        
        function useExample(text) {
            document.getElementById('query').value = text;
        }
        
        function getAnswer() {
            const query = document.getElementById('query').value;
            if (!query) {
                alert('Please enter a query');
                return;
            }
            
            document.getElementById('loader').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            
            fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('loader').style.display = 'none';
                document.getElementById('result').style.display = 'block';
                
                // Set the query type badge
                const queryType = data.query_type || 'general';
                document.getElementById('query-type-badge').innerText = 
                    queryType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                // Clear previous result
                document.getElementById('result-content').innerHTML = '';
                
                if (data.error) {
                    document.getElementById('result-content').innerHTML = `<p class="error">${data.error}</p>`;
                    if (data.raw_response) {
                        document.getElementById('result-content').innerHTML += `<p>${data.raw_response}</p>`;
                    }
                } else {
                    // Display different content based on query type
                    switch(queryType) {
                        case 'price_prediction':
                            document.getElementById('result-content').innerHTML = `
                                <p><strong>Predicted Price:</strong> ₹${data.predicted_price_lakhs} lakhs</p>
                                <p><strong>Price Range:</strong> ${data.predicted_price_range || 'N/A'}</p>
                                <h4>Explanation:</h4>
                                <p>${data.explanation}</p>
                            `;
                            break;
                        case 'market_trend':
                            document.getElementById('result-content').innerHTML = `
                                <p><strong>Market Direction:</strong> ${data.market_direction}</p>
                                <p><strong>Expected Annual Growth:</strong> ${data.expected_annual_growth_percent}%</p>
                                <h4>Analysis:</h4>
                                <p>${data.analysis}</p>
                            `;
                            break;
                        case 'comparison':
                            document.getElementById('result-content').innerHTML = `
                                <h4>Comparison:</h4>
                                <pre>${data.comparison_table}</pre>
                                <p><strong>Recommendation:</strong> ${data.recommendation}</p>
                                <h4>Reasoning:</h4>
                                <p>${data.reasoning}</p>
                            `;
                            break;
                        case 'investment_advice':
                            document.getElementById('result-content').innerHTML = `
                                <p><strong>Investment Recommendation:</strong> ${data.investment_recommendation}</p>
                                <p><strong>Projected Annual ROI:</strong> ${data.projected_annual_roi_percent}%</p>
                                <h4>Investment Analysis:</h4>
                                <p>${data.investment_analysis}</p>
                            `;
                            break;
                        case 'regulation':
                            document.getElementById('result-content').innerHTML = `
                                <h4>Legal Information:</h4>
                                <p>${data.legal_information}</p>
                                <h4>Practical Steps:</h4>
                                <p>${data.practical_steps}</p>
                                <p class="disclaimer"><i>${data.disclaimer}</i></p>
                            `;
                            break;
                        default:
                            document.getElementById('result-content').innerHTML = `
                                <h4>Answer:</h4>
                                <p>${data.answer}</p>
                            `;
                            if (data.references) {
                                document.getElementById('result-content').innerHTML += `
                                    <h4>References:</h4>
                                    <p>${data.references}</p>
                                `;
                            }
                    }
                }
            })
            .catch(error => {
                document.getElementById('loader').style.display = 'none';
                alert('Error: ' + error.message);
            });
        }
        
        function checkDataStatus(city) {
            fetch(`/data_status?city=${city}`)
                .then(response => response.json())
                .then(data => {
                    // Update the UI with data status
                    let statusHTML = '';
                    if (data.status === 'no_data') {
                        statusHTML = `<div class="data-status">
                            <span>${data.city}: </span>
                            <span class="data-status-stale">No data available</span>
                            <button onclick="refreshData('${data.city}')" class="refresh-button">Refresh</button>
                        </div>`;
                    } else {
                        const freshClass = data.is_fresh ? 'data-status-fresh' : 'data-status-stale';
                        statusHTML = `<div class="data-status">
                            <span>${data.city}: </span>
                            <span class="${freshClass}">Last updated: ${data.last_updated} (${Math.round(data.age_hours)} hours ago)</span>
                            <button onclick="refreshData('${data.city}')" class="refresh-button">Refresh</button>
                        </div>`;
                    }
                    
                    // Update query data status if it's for the city in the query
                    const queryCity = document.getElementById('query').value.toLowerCase();
                    if (queryCity.includes(city.toLowerCase())) {
                        document.getElementById('query-data-status').innerHTML = statusHTML;
                    }
                    
                    // Add to data status container in the Data tab
                    if (document.getElementById('data-status-container').innerHTML.includes('Loading')) {
                        document.getElementById('data-status-container').innerHTML = statusHTML;
                    } else {
                        document.getElementById('data-status-container').innerHTML += statusHTML;
                    }
                })
                .catch(error => {
                    console.error('Error checking data status:', error);
                });
        }
        
        function loadAllDataStatus() {
            document.getElementById('data-status-container').innerHTML = 'Loading data status...';
            checkDataStatus('Mumbai');
            checkDataStatus('Bangalore');
            checkDataStatus('Delhi');
        }
        
        function refreshData(city) {
            const statusDiv = document.getElementById('refresh-status');
            statusDiv.innerHTML = `<p>Refreshing data for ${city}...</p>`;
            
            fetch('/refresh_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ cities: [city] })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.innerHTML = `<p>${data.message}</p>`;
                // After a few seconds, check the data status again
                setTimeout(() => {
                    loadAllDataStatus();
                }, 2000);
            })
            .catch(error => {
                statusDiv.innerHTML = `<p>Error: ${error.message}</p>`;
            });
        }
        
        function refreshAllData() {
            const statusDiv = document.getElementById('refresh-status');
            statusDiv.innerHTML = '<p>Refreshing data for all cities...</p>';
            
            fetch('/refresh_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ cities: ['Mumbai', 'Bangalore', 'Delhi'] })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.innerHTML = `<p>${data.message}</p>`;
                // After a few seconds, check the data status again
                setTimeout(() => {
                    loadAllDataStatus();
                }, 2000);
            })
            .catch(error => {
                statusDiv.innerHTML = `<p>Error: ${error.message}</p>`;
            });
        }
    </script>
</body>
</html>
        """)
    
    return app

def cli_mode():
    """Run the application in CLI mode"""
    print("\n" + "="*50)
    print("REAL ESTATE PRICE PREDICTION CLI")
    print("="*50 + "\n")
    
    print("Available cities: Mumbai, Bangalore, Delhi")
    print("Example query: Estimate the price of a 3 BHK apartment in Koramangala, Bangalore with 1500 sq.ft area.\n")
    
    while True:
        user_query = input("Enter your query (or 'exit' to quit): ")
        
        if user_query.lower() in ['exit', 'quit', 'q']:
            print("\nThank you for using Real Estate Price Predictor!")
            break
        
        print("\nProcessing your query...\n")
        result = predictor.predict_price(user_query)
        print(format_prediction_for_cli(result))
        print("\n")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Real Estate Price Prediction")
    parser.add_argument("--web", action="store_true", help="Run in web mode (Flask)")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--scrape", action="store_true", help="Run web scraping")
    args = parser.parse_args()
    
    # Generate data files if they don't exist
    from data_generator import generate_all_city_data
    print("Checking for data files...")
    for city in CITIES:
        file_path = os.path.join(DATA_DIR, f"{city.lower()}.csv")
        if not os.path.exists(file_path):
            print(f"Data file for {city} not found. Generating data...")
            generate_all_city_data()
            break
    
    # Start the scraping scheduler in a separate thread if running with web mode
    if args.web or not (args.cli or args.scrape):
        scheduler_thread = threading.Thread(target=schedule_scraping)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    # If scrape flag is passed, run scraping immediately
    if args.scrape:
        print("Running web scraping...")
        scraper = RealEstateDataScraper()
        scraper.run_scraping()
    # If no mode is specified or --web is provided, run in web mode
    elif args.web or not args.cli:
        app = create_flask_app()
        print(f"Running web server on http://{FLASK_HOST}:{FLASK_PORT}")
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
    else:
        cli_mode()
