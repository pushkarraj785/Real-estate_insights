#!/usr/bin/env python3
"""
Main entry script to run the Real Estate Analysis application
with convenient command-line options
"""

import os
import sys
import argparse
import subprocess

def check_env():
    """Check if environment is properly set up"""
    if not os.path.exists('.env'):
        print("Warning: No .env file found with API keys.")
        create = input("Would you like to create it now? (y/n): ")
        if create.lower() == 'y':
            subprocess.run([sys.executable, "create_env_file.py"])
        else:
            print("Warning: You will need to create a .env file with your API keys to use all features.")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Real Estate AI Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py web         # Run the web application
  python run.py cli         # Run in command line mode
  python run.py scrape      # Run data scraping
  python run.py check       # Check dependencies and configuration
  python run.py setup       # Set up API keys and configuration
        """
    )
    
    parser.add_argument('mode', choices=['web', 'cli', 'scrape', 'check', 'setup'], 
                        help='Operation mode')
    
    parser.add_argument('--refresh', action='store_true', 
                        help='Force refresh of data before starting')
    
    parser.add_argument('--debug', action='store_true', 
                        help='Run in debug mode with verbose output')
    
    args = parser.parse_args()
    
    # Check environment setup for API keys
    if args.mode not in ['check', 'setup']:
        check_env()
    
    # Run in the specified mode
    if args.mode == 'web':
        cmd = [sys.executable, "app.py", "--web"]
        if args.refresh:
            print("Refreshing data first...")
            subprocess.run([sys.executable, "app.py", "--scrape"])
        subprocess.run(cmd)
        
    elif args.mode == 'cli':
        cmd = [sys.executable, "app.py", "--cli"]
        subprocess.run(cmd)
        
    elif args.mode == 'scrape':
        cmd = [sys.executable, "app.py", "--scrape"]
        subprocess.run(cmd)
        
    elif args.mode == 'check':
        cmd = [sys.executable, "check_versions.py"]
        subprocess.run(cmd)
        
        # Also check data status
        print("\nChecking data files:")
        from config import CITIES, DATA_DIR
        for city in CITIES:
            path = os.path.join(DATA_DIR, f"{city.lower()}.csv")
            if os.path.exists(path):
                size = os.path.getsize(path) / 1024  # Size in KB
                print(f"- {city}: Found ({size:.1f} KB)")
            else:
                print(f"- {city}: Not found")
        
    elif args.mode == 'setup':
        cmd = [sys.executable, "create_env_file.py"]
        subprocess.run(cmd)
        
        # Ask if they want to generate initial data
        generate = input("Would you like to generate initial data? (y/n): ")
        if generate.lower() == 'y':
            subprocess.run([sys.executable, "app.py", "--scrape"])

if __name__ == "__main__":
    main()
