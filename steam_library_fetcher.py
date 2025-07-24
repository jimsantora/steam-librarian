#!/usr/bin/env python3
"""
Steam Library Data Fetcher using Steam's 1st party web api as well as their 
unofficial store api for game details. All api requests go directly to Valve/Steam servers.

Fetches detailed information about games in a Steam user's library including:
- Game details (name, appid)
- Maturity/age ratings
- Date added to library
- User review summaries
- Genres and tags
- Developer and publisher info

Usage:
    Set environment variables in .env file:
    - STEAM_ID: Your Steam ID
    - STEAM_API_KEY: Your Steam API key
    
    Run: python steam_library_fetcher.py
"""

import os
import sys
import time
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import requests

from database import (
    get_db, create_database, get_or_create,
    Game, UserGame, Genre, Developer, Publisher, Category, 
    GameReview, UserProfile
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SteamLibraryFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        # Add headers for API requests
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.rate_limit_delay = 1.0  # Seconds between API calls
        self.last_api_call = 0
        
    def _rate_limit(self):
        """Implement rate limiting to avoid hitting API limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        if time_since_last_call < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_call)
        self.last_api_call = time.time()
        
    def get_owned_games(self, steam_id: str) -> List[Dict]:
        """Get list of games owned by the user using direct Steam Web API"""
        logger.info("Fetching owned games...")
        
        try:
            # Direct call to IPlayerService/GetOwnedGames
            url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'include_appinfo': True,
                'include_played_free_games': True,
                'format': 'json'
            }
            
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request params: {params}")
            
            response = self.session.get(url, params=params, timeout=30)
            
            logger.debug(f"Full request URL: {response.url}")
            logger.debug(f"Response headers: {response.headers}")
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'games' in data['response']:
                    games = data['response']['games']
                    logger.info(f"Found {len(games)} games in library")
                    return games
                else:
                    logger.error("No games found in response")
                    return []
            else:
                logger.error(f"Steam API returned {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching owned games: {e}")
            return []
            
    def get_app_details(self, appid: int) -> Optional[Dict]:
        """Get detailed information about a specific app/game from Store API"""
        self._rate_limit()
        
        url = f"https://store.steampowered.com/api/appdetails"
        params = {
            'appids': appid,
            'cc': 'us',
            'l': 'english'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if str(appid) in data and data[str(appid)].get('success'):
                    return data[str(appid)]['data']
            else:
                logger.debug(f"Store API returned {response.status_code} for appid {appid}")
                
        except Exception as e:
            logger.debug(f"Error fetching app details for {appid}: {e}")
            
        return None
        
    def get_app_reviews(self, appid: int) -> Optional[Dict]:
        """Get review summary for an app"""
        self._rate_limit()
        
        # Try using the Steam API first
        try:
            # Note: python-steam-api doesn't have a direct method for reviews
            # So we'll make a direct API call
            url = f"https://store.steampowered.com/appreviews/{appid}"
            params = {
                'json': '1',
                'language': 'all',
                'purchase_type': 'all',
                'num_per_page': '0'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'query_summary' in data:
                    return data['query_summary']
            else:
                logger.debug(f"Review API returned {response.status_code} for appid {appid}")
                
        except Exception as e:
            logger.debug(f"Error fetching reviews for {appid}: {e}")
            
        return None
        
    def process_game(self, game: Dict, index: int, total: int) -> Dict:
        """Process a single game and gather all required information"""
        appid = game.get('appid')
        name = game.get('name', 'Unknown')
        
        # Progress indicator
        logger.info(f"Processing [{index}/{total}]: {name} (AppID: {appid})")
        
        game_info = {
            'appid': appid,
            'name': name,
            'playtime_forever': game.get('playtime_forever', 0),
            'playtime_2weeks': game.get('playtime_2weeks', 0),
            'maturity_rating': 'Unknown',
            'required_age': 0,
            'content_descriptors': '',
            'genres': '',
            'categories': '',
            'developers': '',
            'publishers': '',
            'release_date': '',
            'review_summary': 'Unknown',
            'review_score': 0,
            'total_reviews': 0,
            'positive_reviews': 0,
            'negative_reviews': 0
        }
        
        # Get detailed app information
        app_details = self.get_app_details(appid)
        if app_details:
            # Extract maturity/age rating info
            try:
                game_info['required_age'] = int(app_details.get('required_age', 0))
            except (ValueError, TypeError):
                game_info['required_age'] = 0
            
            # Content descriptors (mature content)
            if 'content_descriptors' in app_details:
                descriptors = app_details['content_descriptors']
                notes = descriptors.get('notes', '')
                ids = descriptors.get('ids', [])
                game_info['content_descriptors'] = notes if notes else ''
            
            # Genres
            genres = app_details.get('genres', [])
            game_info['genres'] = ', '.join([g.get('description', '') for g in genres])
            
            # Categories
            categories = app_details.get('categories', [])
            game_info['categories'] = ', '.join([c.get('description', '') for c in categories])
            
            # Developers and Publishers
            game_info['developers'] = ', '.join(app_details.get('developers', []))
            game_info['publishers'] = ', '.join(app_details.get('publishers', []))
            
            # Release date
            release_date = app_details.get('release_date', {})
            game_info['release_date'] = release_date.get('date', '')
            
            # Determine maturity rating based on age requirement
            if game_info['required_age'] >= 18:
                game_info['maturity_rating'] = 'Mature (18+)'
            elif game_info['required_age'] >= 17:
                game_info['maturity_rating'] = 'Mature (17+)'
            elif game_info['required_age'] >= 13:
                game_info['maturity_rating'] = 'Teen (13+)'
            elif game_info['required_age'] > 0:
                game_info['maturity_rating'] = f'Ages {game_info["required_age"]}+'
            else:
                game_info['maturity_rating'] = 'Everyone'
        
        # Get review information
        reviews = self.get_app_reviews(appid)
        if reviews:
            game_info['review_summary'] = reviews.get('review_score_desc', 'Unknown')
            game_info['review_score'] = reviews.get('review_score', 0)
            game_info['total_reviews'] = reviews.get('total_reviews', 0)
            game_info['positive_reviews'] = reviews.get('total_positive', 0)
            game_info['negative_reviews'] = reviews.get('total_negative', 0)
        
        return game_info
        
    def save_to_database(self, game_data: Dict, steam_id: str):
        """Save game data to SQLite database using SQLAlchemy"""
        with get_db() as session:
            app_id = game_data['appid']
            
            # Create or update game
            game = session.query(Game).filter_by(app_id=app_id).first()
            if not game:
                game = Game(
                    app_id=app_id,
                    name=game_data['name'],
                    maturity_rating=game_data['maturity_rating'],
                    required_age=game_data['required_age'],
                    content_descriptors=game_data['content_descriptors'],
                    release_date=game_data['release_date'],
                    last_updated=int(datetime.now().timestamp())
                )
                session.add(game)
                session.flush()
            else:
                # Update existing game data
                game.name = game_data['name']
                game.maturity_rating = game_data['maturity_rating']
                game.required_age = game_data['required_age']
                game.content_descriptors = game_data['content_descriptors']
                game.release_date = game_data['release_date']
                game.last_updated = int(datetime.now().timestamp())
            
            # Handle genres
            if game_data['genres']:
                # Clear existing genres for this game
                game.genres.clear()
                for genre_name in game_data['genres'].split(', '):
                    if genre_name.strip():
                        genre = get_or_create(session, Genre, genre_name=genre_name.strip())
                        game.genres.append(genre)
            
            # Handle developers
            if game_data['developers']:
                game.developers.clear()
                for dev_name in game_data['developers'].split(', '):
                    if dev_name.strip():
                        developer = get_or_create(session, Developer, developer_name=dev_name.strip())
                        game.developers.append(developer)
            
            # Handle publishers
            if game_data['publishers']:
                game.publishers.clear()
                for pub_name in game_data['publishers'].split(', '):
                    if pub_name.strip():
                        publisher = get_or_create(session, Publisher, publisher_name=pub_name.strip())
                        game.publishers.append(publisher)
            
            # Handle categories
            if game_data['categories']:
                game.categories.clear()
                for cat_name in game_data['categories'].split(', '):
                    if cat_name.strip():
                        category = get_or_create(session, Category, category_name=cat_name.strip())
                        game.categories.append(category)
            
            # Handle reviews
            if game_data['review_summary'] != 'Unknown' or game_data['total_reviews'] > 0:
                review = session.query(GameReview).filter_by(app_id=app_id).first()
                if not review:
                    review = GameReview(
                        app_id=app_id,
                        review_summary=game_data['review_summary'],
                        review_score=game_data['review_score'],
                        total_reviews=game_data['total_reviews'],
                        positive_reviews=game_data['positive_reviews'],
                        negative_reviews=game_data['negative_reviews'],
                        last_updated=int(datetime.now().timestamp())
                    )
                    session.add(review)
                else:
                    # Update existing review
                    review.review_summary = game_data['review_summary']
                    review.review_score = game_data['review_score']
                    review.total_reviews = game_data['total_reviews']
                    review.positive_reviews = game_data['positive_reviews']
                    review.negative_reviews = game_data['negative_reviews']
                    review.last_updated = int(datetime.now().timestamp())
            
            # Handle user game data
            user_game = session.query(UserGame).filter_by(
                steam_id=steam_id, 
                app_id=app_id
            ).first()
            
            if not user_game:
                user_game = UserGame(
                    steam_id=steam_id,
                    app_id=app_id,
                    playtime_forever=game_data['playtime_forever'],
                    playtime_2weeks=game_data['playtime_2weeks']
                )
                session.add(user_game)
            else:
                # Update playtime data
                user_game.playtime_forever = max(user_game.playtime_forever, game_data['playtime_forever'])
                user_game.playtime_2weeks = game_data['playtime_2weeks']
            
            session.commit()
        
    def fetch_library_data(self, steam_id: str):
        """Main method to fetch all library data and save to database"""
        # Create database tables if they don't exist
        create_database()
        
        # Create user profile if it doesn't exist
        with get_db() as session:
            user = session.query(UserProfile).filter_by(steam_id=steam_id).first()
            if not user:
                user = UserProfile(
                    steam_id=steam_id,
                    last_updated=int(datetime.now().timestamp())
                )
                session.add(user)
                session.commit()
                logger.info(f"Created user profile for Steam ID: {steam_id}")
        
        # Get owned games
        owned_games = self.get_owned_games(steam_id)
        if not owned_games:
            logger.error("No games found in library")
            return
        
        total_games = len(owned_games)
        failed_count = 0
        processed_count = 0
        
        logger.info(f"Starting to process {total_games} games...")
        logger.info("This may take a while due to rate limiting...")
        logger.info("Note: Some games may not have store data available (403 errors are normal)")
        
        for index, game in enumerate(owned_games, 1):
            try:
                game_data = self.process_game(game, index, total_games)
                # Save to database immediately
                self.save_to_database(game_data, steam_id)
                processed_count += 1
                
                # Show progress every 10 games
                if index % 10 == 0:
                    estimated_time = (total_games - index) * self.rate_limit_delay
                    logger.info(f"Progress: {index}/{total_games} games processed. Estimated time remaining: {estimated_time:.0f} seconds")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing game {game.get('name', 'Unknown')}: {e}")
                # Still save basic info even if detailed processing fails
                fallback_data = {
                    'appid': game.get('appid'),
                    'name': game.get('name', 'Unknown'),
                    'playtime_forever': game.get('playtime_forever', 0),
                    'playtime_2weeks': game.get('playtime_2weeks', 0),
                    'maturity_rating': 'Unknown',
                    'required_age': 0,
                    'content_descriptors': '',
                    'genres': '',
                    'categories': '',
                    'developers': '',
                    'publishers': '',
                    'release_date': '',
                    'review_summary': 'Unknown',
                    'review_score': 0,
                    'total_reviews': 0,
                    'positive_reviews': 0,
                    'negative_reviews': 0
                }
                try:
                    self.save_to_database(fallback_data, steam_id)
                    processed_count += 1
                except Exception as db_error:
                    logger.error(f"Failed to save fallback data for {game.get('name', 'Unknown')}: {db_error}")
                
        if failed_count > 0:
            logger.warning(f"Note: {failed_count} games had limited data due to API restrictions")
        
        logger.info(f"Completed! Processed {processed_count} games successfully. Data saved to database")
        
def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for debug flag
    debug = '--debug' in sys.argv
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get environment variables
    steam_id = os.getenv('STEAM_ID')
    api_key = os.getenv('STEAM_API_KEY')
    
    if not steam_id or not api_key:
        logger.error("Missing environment variables!")
        logger.error("Please set STEAM_ID and STEAM_API_KEY in your .env file")
        sys.exit(1)
        
    logger.info(f"Starting Steam Library Fetcher for Steam ID: {steam_id}")
    
    # Create fetcher and run
    fetcher = SteamLibraryFetcher(api_key)
    fetcher.fetch_library_data(steam_id)
    
if __name__ == "__main__":
    main()