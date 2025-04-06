# Real Estate Insights - AI-Powered Analysis Tool

A sophisticated application that provides AI-powered insights and predictions for the Indian real estate market by collecting, analyzing, and processing real-time property data from various sources.

![Real Estate Insights](https://via.placeholder.com/800x400?text=Real+Estate+Insights+Dashboard)

## 🏠 Overview

This application helps users make informed decisions about real estate investments in major Indian cities. It combines web scraping from commercial property websites and government sources with AI-powered analysis to provide accurate property price predictions and market insights.

## ✨ Features

- **Real-time Property Price Prediction**: Get accurate price estimates based on location, size, and amenities
- **Market Trend Analysis**: Understand how property prices are evolving in various localities
- **Property Comparison**: Compare investment potential between different areas
- **Investment Advice**: Receive AI-generated investment recommendations based on current market conditions
- **Regulatory Information**: Access relevant legal and regulatory information for property transactions
- **Multiple Interfaces**: Use either the web interface or command-line interface based on your preference

## 🌆 Supported Cities

- Mumbai
- Bangalore
- Delhi

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection for web scraping

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/real-estate-insights.git
   cd real-estate-insights
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   # Create .env file with API keys
   python create_env_file.py
   ```

4. Generate initial data (optional):
   ```bash
   python data_generator.py
   ```

## 🔧 Configuration

The application can be configured through several files:

- `.env`: Contains API keys and scraping configuration
- `config.py`: Contains application-wide settings and parameters

### Environment Variables

Create a `.env` file with the following variables:

```
GEMINI_API_KEY=your_gemini_api_key_here
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36
HOUSING_URL_FORMAT=https://housing.com/in/buy/search-real-estate-to-buy-in-{city}?page={page}
MAGICBRICKS_URL_FORMAT=https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName={city}&page={page}
REQUEST_TIMEOUT=30
ENABLE_MAGICBRICKS=true
ENABLE_HOUSING=true
ENABLE_GOVERNMENT=true
REQUEST_DELAY=2
```

## 💻 Usage

### Web Interface

1. Run the web application:
   ```bash
   python app.py --web
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Use the interface to ask questions or request predictions about real estate properties

### Command Line Interface

1. Run the CLI application:
   ```bash
   python app.py --cli
   ```

2. Follow the prompts to enter your real estate queries

### Data Scraping

To manually trigger data scraping:

```bash
python app.py --scrape
```

## 🔁 Data Pipeline

1. **Data Collection**: Web scraping from commercial websites (Magicbricks, Housing.com) and government sources
2. **Data Processing**: Cleaning, normalization, and consolidation of collected data
3. **Data Storage**: Storage in CSV files organized by city
4. **Data Analysis**: AI-powered analysis using Google's Gemini model
5. **Insight Generation**: Creating actionable insights based on analysis

## 📊 Data Sources

- **Commercial Websites**: 
  - Magicbricks.com
  - Housing.com
- **Government Sources**:
  - Maharashtra RERA (Real Estate Regulatory Authority)
  - Delhi government property databases
  - Bangalore government property records
- **Generated Data**: For demonstration purposes when real data is unavailable

## 🧠 AI Model

The application uses Google's Gemini model for:
- Price prediction
- Market trend analysis
- Comparison of properties
- Investment advice
- Regulatory information
- Answering general real estate queries

## 📁 Project Structure

```
real-estate-insights/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── data_generator.py       # Generates sample data
├── llm_predictor.py        # Gemini AI integration
├── run.py                  # Entry point script
├── scraper.py              # Web scraping functionality
├── utils/                  # Utility modules
│   ├── scraper_config.py   # Scraping configuration utilities
│   └── error_handler.py    # Error handling utilities
├── data/                   # Data storage directory
│   ├── mumbai/             # Mumbai-specific data
│   ├── bangalore/          # Bangalore-specific data
│   └── delhi/              # Delhi-specific data
└── templates/              # HTML templates
    └── index.html          # Main web interface
```

## 🔒 Security and Rate Limiting

To respect website terms of service and avoid being blocked:
- Random delays between requests
- Rotating user agents
- Proper error handling with exponential backoff
- Configurable request limits

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📬 Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/real-estate-insights](https://github.com/yourusername/real-estate-insights)

## 🙏 Acknowledgments

- Google's Gemini AI model for powering the insights
- Flask for the web framework
- Beautiful Soup for web scraping
- The open-source community for various libraries and tools
