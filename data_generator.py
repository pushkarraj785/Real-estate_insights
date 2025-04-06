import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from config import DATA_DIR

def generate_city_data(city, num_records=1500):
    """
    Generate dummy real estate data for demonstration
    
    Args:
        city (str): City name
        num_records (int): Number of records to generate
    
    Returns:
        pd.DataFrame: Generated data
    """
    np.random.seed(42)  # For reproducibility
    
    # Base parameters for different cities (all prices in lakhs INR)
    city_params = {
        "Mumbai": {
            "localities": ["Andheri", "Bandra", "Worli", "Powai", "Juhu", "Malad", "Goregaon"],
            "price_mean": 30000,  # per sq ft
            "price_std": 8000,
            "area_mean": 1000,
            "area_std": 300
        },
        "Bangalore": {
            "localities": ["Koramangala", "HSR Layout", "Indiranagar", "Whitefield", "Electronic City", "Jayanagar"],
            "price_mean": 8000,
            "price_std": 2000,
            "area_mean": 1200,
            "area_std": 350
        },
        "Delhi": {
            "localities": ["Vasant Kunj", "Dwarka", "Rohini", "Greater Kailash", "South Extension", "Mayur Vihar"],
            "price_mean": 15000,
            "price_std": 4500,
            "area_mean": 1100,
            "area_std": 320
        }
    }
    
    params = city_params[city]
    
    # Generate data
    data = {
        "city": [city] * num_records,
        "locality": [np.random.choice(params["localities"]) for _ in range(num_records)],
        "property_type": np.random.choice(["Apartment", "Villa", "Plot", "Row House"], num_records, p=[0.7, 0.15, 0.1, 0.05]),
        "bedrooms": np.random.choice([1, 2, 3, 4, 5], num_records, p=[0.1, 0.3, 0.4, 0.15, 0.05]),
        "area_sqft": np.round(np.random.normal(params["area_mean"], params["area_std"], num_records)),
        "price_per_sqft": np.round(np.random.normal(params["price_mean"], params["price_std"], num_records)),
        "transaction_date": [(datetime.now() - timedelta(days=np.random.randint(1, 365))).strftime('%Y-%m-%d') for _ in range(num_records)]
    }
    
    # Calculate total price (in lakhs)
    data["price_total"] = np.round(data["area_sqft"] * data["price_per_sqft"] / 100000, 2)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Clean up data
    df = df[df["area_sqft"] > 0]
    
    return df

def generate_all_city_data():
    """Generate and save dummy data for all cities in config"""
    from config import CITIES
    
    for city in CITIES:
        df = generate_city_data(city, num_records=200)
        
        # Save to CSV
        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"{city.lower()}.csv")
        df.to_csv(file_path, index=False)
        print(f"Generated data for {city} saved to {file_path}")

if __name__ == "__main__":
    generate_all_city_data()
