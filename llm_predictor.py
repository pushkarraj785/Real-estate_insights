import pandas as pd
import os
import json
import logging
import time
import random
import re
import glob
from datetime import datetime, timedelta
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, DATA_DIR, MAX_CONTEXT_RECORDS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure Gemini API client
genai.configure(api_key=GEMINI_API_KEY)

class LLMRealEstatePricePredictor:
    def __init__(self):
        self.model = GEMINI_MODEL
        self.data_dir = DATA_DIR
        
        # Configure retry parameters
        self.max_retries = 5
        self.base_delay = 1  # Initial delay in seconds
        self.max_delay = 60  # Maximum delay in seconds
        
        # Question types and corresponding handlers
        self.question_types = {
            "price_prediction": self._handle_price_prediction,
            "market_trend": self._handle_market_trend,
            "comparison": self._handle_comparison,
            "investment_advice": self._handle_investment_advice,
            "regulation": self._handle_regulation_query,
            "general": self._handle_general_query
        }
    
    def load_city_data(self, city):
        """
        Load property data for a specific city
        
        Args:
            city (str): Name of the city
            
        Returns:
            pd.DataFrame: City property data
        """
        try:
            file_path = os.path.join(self.data_dir, f"{city.lower()}.csv")
            if not os.path.exists(file_path):
                logger.warning(f"Data file for {city} not found at {file_path}")
                return None
            
            return pd.read_csv(file_path)
        except Exception as e:
            logger.error(f"Error loading data for {city}: {str(e)}")
            return None
    
    def load_recent_city_data(self, city, days=30):
        """
        Load recent property data for a specific city from all available sources
        
        Args:
            city (str): Name of the city
            days (int): Number of days to consider recent data
            
        Returns:
            pd.DataFrame: Recent city property data
        """
        try:
            # Get the city directory
            city_dir = os.path.join(self.data_dir, city.lower())
            
            if not os.path.exists(city_dir):
                logger.warning(f"Directory for {city} not found at {city_dir}")
                return self.load_city_data(city)  # Fall back to consolidated file
            
            # Find all CSV files in the city directory
            csv_files = glob.glob(os.path.join(city_dir, "*.csv"))
            
            # Filter files based on modification time
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_files = [f for f in csv_files if os.path.getmtime(f) >= cutoff_date.timestamp()]
            
            if not recent_files:
                logger.info(f"No recent data files found for {city}, using all available files")
                recent_files = csv_files
            
            if not recent_files:
                logger.warning(f"No data files found for {city}")
                return self.load_city_data(city)  # Fall back to consolidated file
            
            # Load and combine all recent files
            dfs = []
            for file_path in recent_files:
                try:
                    df = pd.read_csv(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {str(e)}")
            
            if not dfs:
                return self.load_city_data(city)  # Fall back to consolidated file
                
            # Combine all dataframes
            combined_df = pd.concat(dfs).drop_duplicates()
            return combined_df
            
        except Exception as e:
            logger.error(f"Error loading recent data for {city}: {str(e)}")
            return self.load_city_data(city)  # Fall back to consolidated file
    
    def _classify_question(self, user_query):
        """
        Classify the type of real estate question
        
        Args:
            user_query (str): User's query
            
        Returns:
            str: Question type
        """
        query = user_query.lower()
        
        # Price prediction patterns
        if any(x in query for x in ["price", "cost", "worth", "value", "estimate", "how much"]):
            return "price_prediction"
            
        # Market trend patterns
        elif any(x in query for x in ["trend", "growing", "appreciate", "future", "forecast", "predict", "market"]):
            return "market_trend"
            
        # Comparison patterns
        elif any(x in query for x in ["compare", "versus", "vs", "better", "difference between", "which is"]):
            return "comparison"
            
        # Investment advice patterns
        elif any(x in query for x in ["invest", "roi", "return", "profitable", "should i buy", "good time"]):
            return "investment_advice"
            
        # Regulation and legal patterns
        elif any(x in query for x in ["law", "legal", "registration", "tax", "stamp duty", "regulation", "rules"]):
            return "regulation"
            
        # Default to general query
        return "general"
    
    def prepare_context_data(self, user_query):
        """
        Extract city and locality from user query and prepare relevant data context
        
        Args:
            user_query (str): User's real estate query
            
        Returns:
            str: Formatted context data
        """
        # Extract city name from user query
        city = None
        for possible_city in ["Mumbai", "Bangalore", "Delhi"]:
            if possible_city.lower() in user_query.lower():
                city = possible_city
                break
        
        if city is None:
            return "No city data found in query. Please specify a city (Mumbai, Bangalore, or Delhi)."
        
        # Load city data - use recent data where available
        df = self.load_recent_city_data(city)
        if df is None or len(df) == 0:
            return f"No data available for {city}."
        
        # Extract locality if mentioned
        localities = df['locality'].unique()
        target_locality = None
        
        for loc in localities:
            if loc.lower() in user_query.lower():
                target_locality = loc
                break
        
        # Filter data if locality is specified
        if target_locality:
            filtered_df = df[df['locality'] == target_locality]
            if len(filtered_df) > 0:
                df = filtered_df
        
        # Extract property type if mentioned
        property_types = ["Flat", "Villa", "Plot", "Apartment"]
        target_property_type = None
        
        for prop_type in property_types:
            if prop_type.lower() in user_query.lower() or (prop_type == "Flat" and "bhk" in user_query.lower()):
                target_property_type = "Flat" if prop_type == "Apartment" else prop_type
                break
        
        # Filter by property type if specified
        if target_property_type and 'property_type' in df.columns:
            filtered_df = df[df['property_type'] == target_property_type]
            if len(filtered_df) > 0:
                df = filtered_df
        
        # Extract BHK information if mentioned
        bhk = None
        import re
        bhk_match = re.search(r'(\d+)\s*bhk', user_query.lower())
        if bhk_match:
            bhk = int(bhk_match.group(1))
            
            # Filter by bedrooms if specified
            if bhk and 'bedrooms' in df.columns:
                filtered_df = df[df['bedrooms'] == bhk]
                if len(filtered_df) > 0:
                    df = filtered_df
        
        # Sample data for context (to keep within token limits)
        if len(df) > MAX_CONTEXT_RECORDS:
            df = df.sample(MAX_CONTEXT_RECORDS, random_state=42)
        
        # Prepare context data as a string table
        context = f"Real estate data for {city}"
        if target_locality:
            context += f", locality: {target_locality}"
        if target_property_type:
            context += f", property type: {target_property_type}"
        if bhk:
            context += f", {bhk} BHK"
        context += ":\n\n"
        
        # Format as a table
        context += df.to_string(index=False)
        
        # Add summary statistics
        context += "\n\nSummary Statistics:\n"
        context += f"Average price per sq.ft: ₹{df['price_per_sqft'].mean():.2f}\n"
        context += f"Average total price: ₹{df['price_total'].mean():.2f} lakhs\n"
        context += f"Price range: ₹{df['price_total'].min():.2f} - ₹{df['price_total'].max():.2f} lakhs\n"
        context += f"Average area: {df['area_sqft'].mean():.2f} sq.ft\n"
        
        # Add trends if available
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'])
            # Group by month and calculate average prices
            df['month'] = df['transaction_date'].dt.to_period('M')
            monthly_avg = df.groupby('month')['price_per_sqft'].mean().reset_index()
            if len(monthly_avg) > 1:
                context += "\nMonthly Price Trends (per sq.ft):\n"
                for _, row in monthly_avg.iterrows():
                    context += f"{row['month']}: ₹{row['price_per_sqft']:.2f}\n"
        
        return context
    
    def _handle_price_prediction(self, user_query, context_data):
        """Handle price prediction queries"""
        prompt = f"""You are a real estate price prediction expert for Indian properties. 
Based on the following historical real estate data, I want you to:
1. Analyze the provided market data carefully
2. Estimate the price for the property described in the user query
3. Provide a detailed explanation for your estimate, including key factors that influenced your prediction
4. Format your response as a JSON with keys: "predicted_price_lakhs" (numerical value in lakhs INR), "predicted_price_range" (string), and "explanation" (string)

Historical market data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object. Make sure the JSON is properly formatted with keys: predicted_price_lakhs, predicted_price_range, and explanation.
"""
        return prompt
    
    def _handle_market_trend(self, user_query, context_data):
        """Handle market trend queries"""
        prompt = f"""You are a real estate market analyst expert for Indian properties.
Based on the following historical real estate data, I want you to:
1. Analyze the market trends carefully from the provided data
2. Identify whether the market is appreciating, depreciating, or stable
3. Provide insights on future market direction based on historical patterns
4. Format your response as a JSON with keys: "market_direction" (string: "appreciating", "depreciating", or "stable"), "expected_annual_growth_percent" (numerical value), and "analysis" (detailed explanation string)

Historical market data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object.
"""
        return prompt
    
    def _handle_comparison(self, user_query, context_data):
        """Handle comparison queries"""
        prompt = f"""You are a real estate comparison expert for Indian properties.
Based on the following historical real estate data, I want you to:
1. Compare the properties or areas mentioned in the user query
2. Provide pros and cons of each option
3. Recommend the better option based on value for money, future prospects, and amenities
4. Format your response as a JSON with keys: "comparison_table" (string showing key metrics), "recommendation" (string), and "reasoning" (string)

Historical market data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object.
"""
        return prompt
    
    def _handle_investment_advice(self, user_query, context_data):
        """Handle investment advice queries"""
        prompt = f"""You are a real estate investment advisor expert for Indian properties.
Based on the following historical real estate data, I want you to:
1. Analyze the investment potential of the property or area in question
2. Calculate expected ROI based on historical price trends
3. Provide investment recommendations (buy, wait, avoid)
4. Format your response as a JSON with keys: "investment_recommendation" (string), "projected_annual_roi_percent" (numerical value), and "investment_analysis" (string with detailed reasoning)

Historical market data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object.
"""
        return prompt
    
    def _handle_regulation_query(self, user_query, context_data):
        """Handle regulation and legal queries"""
        prompt = f"""You are a real estate legal and regulatory expert for Indian properties.
Based on your knowledge and the following context data, I want you to:
1. Address the legal or regulatory question in the user query
2. Provide information on relevant laws, regulations, or procedures
3. Give practical steps or advice related to the query
4. Format your response as a JSON with keys: "legal_information" (string explaining the relevant laws/regulations), "practical_steps" (string with actionable advice), and "disclaimer" (a disclaimer stating this is not legal advice)

Context data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object.
"""
        return prompt
    
    def _handle_general_query(self, user_query, context_data):
        """Handle general real estate queries"""
        prompt = f"""You are a comprehensive real estate expert for Indian properties.
Based on the following real estate data and your knowledge, I want you to:
1. Answer the user's query about real estate
2. Provide factual information backed by the data where possible
3. Format your response as a JSON with keys: "answer" (detailed response to the query) and "references" (mention of specific data points that support your answer)

Context data:
{context_data}

User query: {user_query}

Respond with only a valid JSON object.
"""
        return prompt
    
    def _call_gemini_with_backoff(self, prompt):
        """
        Call Gemini API with exponential backoff for rate limiting
        
        Args:
            prompt (str): The prompt to send to the Gemini API
            
        Returns:
            str: Response text from Gemini
            
        Raises:
            Exception: If max retries exceeded or other errors occur
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                # Initialize Gemini model
                model = genai.GenerativeModel(self.model)
                
                # Call the Gemini API
                response = model.generate_content(prompt)
                
                # Return the response text
                return response.text
                
            except Exception as e:
                retries += 1
                error_msg = str(e)
                logger.error(f"Gemini API error: {error_msg}")
                
                # If quota error, raise immediately
                if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    logger.error("API quota or rate limit error")
                    raise e
                
                # Max retries reached
                if retries > self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded")
                    raise e
                
                # Calculate delay with exponential backoff and jitter
                delay = min(self.base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), self.max_delay)
                logger.info(f"Retrying in {delay:.2f} seconds (attempt {retries}/{self.max_retries})")
                time.sleep(delay)
    
    def predict_price(self, user_query):
        """
        Legacy method for backwards compatibility
        Predicts real estate price using Gemini LLM
        
        Args:
            user_query (str): User's real estate query
            
        Returns:
            dict: Prediction result with price and explanation
        """
        return self.answer_query(user_query)
    
    def answer_query(self, user_query):
        """
        Answer any real estate related query using Gemini LLM
        
        Args:
            user_query (str): User's real estate query
            
        Returns:
            dict: Answer result with relevant information
        """
        try:
            # Classify the question type
            question_type = self._classify_question(user_query)
            logger.info(f"Question classified as: {question_type}")
            
            # Prepare context data
            context_data = self.prepare_context_data(user_query)
            
            # Get the appropriate prompt handler based on question type
            prompt_handler = self.question_types.get(question_type, self._handle_general_query)
            
            # Construct the prompt using the appropriate handler
            prompt = prompt_handler(user_query, context_data)

            # Call the Gemini API with better error handling and exponential backoff
            try:
                # Use the exponential backoff method
                result_text = self._call_gemini_with_backoff(prompt)
                
                # Parse JSON from the response
                # First, try to extract the JSON from the response if it's wrapped in markdown code blocks
                if "```json" in result_text:
                    # Extract JSON from code blocks
                    json_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    # Extract from generic code blocks
                    json_text = result_text.split("```")[1].strip()
                else:
                    # Use the raw response
                    json_text = result_text.strip()
                
                try:
                    # Try to parse as JSON
                    result = json.loads(json_text)
                    
                    # Add question type to result
                    result["query_type"] = question_type
                    
                    return result
                except json.JSONDecodeError:
                    # If not valid JSON, try to clean it more aggressively
                    logger.warning("Failed to parse JSON response, attempting to clean")
                    
                    # Remove common issues like line breaks and extra quotes
                    cleaned_text = result_text.replace('\n', ' ').strip()
                    
                    # Try to find anything that looks like JSON
                    import re
                    json_pattern = r'\{.*\}'
                    json_match = re.search(json_pattern, cleaned_text)
                    
                    if json_match:
                        try:
                            result = json.loads(json_match.group(0))
                            result["query_type"] = question_type
                            return result
                        except json.JSONDecodeError:
                            return {
                                "error": "Failed to parse Gemini response as JSON",
                                "raw_response": result_text,
                                "query_type": question_type
                            }
                    else:
                        return {
                            "error": "Failed to parse Gemini response",
                            "raw_response": result_text,
                            "query_type": question_type
                        }
                    
            except Exception as e:
                logger.error(f"Error calling Gemini API: {str(e)}")
                return {
                    "error": f"Gemini API error: {str(e)}",
                    "details": "Please check your API key and network connection.",
                    "query_type": question_type
                }
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {"error": str(e)}

if __name__ == "__main__":
    # Simple test
    predictor = LLMRealEstatePricePredictor()
    query = "Estimate the price of a 3 BHK apartment in Koramangala, Bangalore with 1500 sq.ft area."
    result = predictor.answer_query(query)
    print(json.dumps(result, indent=2))
    
    # Test other query types
    queries = [
        "What's the trend for property prices in Bandra, Mumbai over the last year?",
        "Compare investment potential between Whitefield and HSR Layout in Bangalore",
        "What are the stamp duty charges for property registration in Delhi?",
        "Is it a good time to invest in a 2 BHK flat in Andheri, Mumbai?"
    ]
    
    for q in queries:
        print("\n" + "="*50)
        print(f"Query: {q}")
        result = predictor.answer_query(q)
        print(json.dumps(result, indent=2))
