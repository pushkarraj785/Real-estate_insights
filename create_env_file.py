import os
import sys

def create_env_file():
    """Create .env file from user input"""
    if os.path.exists('.env'):
        print("An .env file already exists.")
        overwrite = input("Do you want to overwrite it? (y/n): ")
        if overwrite.lower() != 'y':
            print("Keeping existing .env file. Exiting.")
            return
    
    api_key = input("Enter your Gemini API key: ")
    
    with open('.env', 'w') as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
    
    print(".env file created successfully!")
    print("\nTo get a Gemini API key:")
    print("1. Go to https://ai.google.dev/")
    print("2. Create a new API key in the Google AI Studio")
    print("3. Copy your API key and paste it here")

if __name__ == "__main__":
    create_env_file()
