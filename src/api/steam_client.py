"""Steam API client for fetching game and user data"""
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests

from src.core.database import get_db
from src.models import Game

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
        # Cache control attributes
        self.cache_days = 7  # Default to 7 days
        self.force_refresh = False
        self.skip_games = False
        self.fetch_friends = False
        
    def _rate_limit(self):
        """Implement rate limiting to avoid hitting API limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call
        if time_since_last_call < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_call)
        self.last_api_call = time.time()
    
    def _is_game_cached(self, app_id: int) -> bool:
        """Check if game data is recent enough to skip fetching"""
        if self.force_refresh:
            return False
            
        with get_db() as session:
            game = session.query(Game).filter_by(app_id=app_id).first()
            if not game:
                return False
                
            # Check if last_updated is within cache threshold
            if game.last_updated:
                cache_age_seconds = int(datetime.now().timestamp()) - game.last_updated
                cache_age_days = cache_age_seconds / (24 * 60 * 60)
                return cache_age_days < self.cache_days
            
            return False
        
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
        
    def get_player_summaries(self, steam_ids: str) -> List[Dict]:
        """Get player profile information from Steam API (supports single ID or comma-separated list)"""
        logger.info(f"Fetching player profile(s) for Steam ID(s): {steam_ids}")
        
        try:
            url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            params = {
                'key': self.api_key,
                'steamids': steam_ids,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'players' in data['response']:
                    return data['response']['players']
                else:
                    logger.error("Invalid response structure")
                    return []
            else:
                logger.error(f"Steam API returned {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching player summaries: {e}")
            return []
    
    def get_player_badges(self, steam_id: str) -> Optional[Dict]:
        """Get player badges and XP information from Steam API"""
        logger.info(f"Fetching player badges/XP for Steam ID: {steam_id}")
        
        try:
            url = "http://api.steampowered.com/IPlayerService/GetBadges/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,  # Note: singular 'steamid', not 'steamids'
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data:
                    return data['response']
                else:
                    logger.error("Invalid response structure for badges")
                    return None
            else:
                logger.error(f"Steam API returned {response.status_code} for badges")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching player badges: {e}")
            return None
    
    def calculate_steam_level(self, xp: int) -> int:
        """Calculate Steam level from XP using Steam's formula"""
        # Steam's level calculation formula
        # Levels 1-10: 100 XP per level
        # Levels 11-20: 200 XP per level  
        # Levels 21-30: 300 XP per level
        # And so on...
        
        if xp < 100:
            return 0
            
        level = 0
        xp_remaining = xp
        
        # Calculate level based on XP brackets
        bracket_size = 100
        bracket_levels = 10
        
        while xp_remaining > 0:
            xp_for_bracket = bracket_size * bracket_levels
            
            if xp_remaining >= xp_for_bracket:
                level += bracket_levels
                xp_remaining -= xp_for_bracket
                bracket_size += 100
            else:
                level += xp_remaining // bracket_size
                break
                
        return level
    
    def get_friend_list(self, steam_id: str) -> List[Dict]:
        """Get friend list from Steam API"""
        logger.info(f"Fetching friend list for Steam ID: {steam_id}")
        
        try:
            url = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'relationship': 'friend',
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'friendslist' in data and 'friends' in data['friendslist']:
                    return data['friendslist']['friends']
                else:
                    logger.info("No friends found or private profile")
                    return []
            else:
                logger.info(f"Friend list API returned {response.status_code} - likely private profile")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching friend list: {e}")
            return []