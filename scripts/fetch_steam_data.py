#!/usr/bin/env python3
"""
Steam Library Data Fetcher CLI - Entry point for fetching Steam data

Usage:
    Set environment variables in .env file:
    - STEAM_ID: Your Steam ID
    - STEAM_API_KEY: Your Steam API key
    
    Run: python scripts/fetch_steam_data.py
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import create_database
from src.api import SteamLibraryFetcher, SteamDataFetcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Fetch Steam library data with caching support')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--cache-days', type=int, default=7, 
                       help='Maximum age in days before re-fetching game data (default: 7)')
    parser.add_argument('--force-refresh', action='store_true',
                       help='Force refresh all game data, ignoring cache')
    parser.add_argument('--skip-games', action='store_true',
                       help='Skip fetching game details entirely')
    parser.add_argument('--friends', action='store_true',
                       help='Also fetch friends list and their game libraries')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get environment variables (support both .env and env vars)
    steam_id = os.getenv('STEAM_ID')
    api_key = os.getenv('STEAM_API_KEY')
    
    # Also check for CACHE_DAYS env var
    cache_days = int(os.getenv('CACHE_DAYS', args.cache_days))
    
    if not steam_id or not api_key:
        logger.error("Missing environment variables!")
        logger.error("Please set STEAM_ID and STEAM_API_KEY in your .env file")
        sys.exit(1)
        
    logger.info(f"Starting Steam Library Fetcher for Steam ID: {steam_id}")
    if args.force_refresh:
        logger.info("Force refresh enabled - all game data will be re-fetched")
    else:
        logger.info(f"Using cache threshold of {cache_days} days")
    
    # Ensure database is created
    create_database()
    
    # Create fetcher and run
    steam_client = SteamLibraryFetcher(api_key)
    steam_client.cache_days = cache_days
    steam_client.force_refresh = args.force_refresh
    steam_client.skip_games = args.skip_games
    steam_client.fetch_friends = args.friends
    
    fetcher = SteamDataFetcher(steam_client)
    fetcher.run(steam_id)
    

if __name__ == "__main__":
    main()