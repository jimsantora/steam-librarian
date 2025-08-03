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

import argparse
import logging
import os
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher import __version__
from shared.database import (
    Category,
    Developer,
    Game,
    GameReview,
    Genre,
    Publisher,
    Tag,
    UserGame,
    UserProfile,
    create_database,
    friends_association,
    get_db,
    get_db_transaction,
    get_or_create,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SteamLibraryFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        # Add headers for API requests
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
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

    def get_owned_games(self, steam_id: str) -> list[dict]:
        """Get list of games owned by the user using direct Steam Web API"""
        logger.info("Fetching owned games...")

        try:
            # Direct call to IPlayerService/GetOwnedGames
            url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
            params = {"key": self.api_key, "steamid": steam_id, "include_appinfo": True, "include_played_free_games": True, "format": "json"}

            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request params: {params}")

            response = self.session.get(url, params=params, timeout=30)

            logger.debug(f"Full request URL: {response.url}")
            logger.debug(f"Response headers: {response.headers}")

            if response.status_code == 200:
                data = response.json()
                if "response" in data and "games" in data["response"]:
                    games = data["response"]["games"]
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

    def get_app_details(self, appid: int) -> dict | None:
        """Get detailed information about a specific app/game from Store API"""
        self._rate_limit()

        url = "https://store.steampowered.com/api/appdetails"
        params = {"appids": appid, "cc": "us", "l": "english"}

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if str(appid) in data and data[str(appid)].get("success"):
                    return data[str(appid)]["data"]
            else:
                logger.debug(f"Store API returned {response.status_code} for appid {appid}")

        except Exception as e:
            logger.debug(f"Error fetching app details for {appid}: {e}")

        return None

    def get_app_tags(self, appid: int) -> list[str] | None:
        """Get user-generated tags for an app from Steam store page"""
        self._rate_limit()

        url = f"https://store.steampowered.com/app/{appid}/"

        try:
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                return self._extract_tags_from_html(response.text)
            else:
                logger.debug(f"Store page returned {response.status_code} for appid {appid}")

        except Exception as e:
            logger.debug(f"Error fetching tags for {appid}: {e}")

        return None

    def _extract_tags_from_html(self, html_content: str) -> list[str]:
        """Extract tags from Steam store page HTML"""
        import re

        tags = []

        # Pattern to match the tag links within the popular_tags section
        pattern = r'<a[^>]+class="app_tag"[^>]*>(.*?)</a>'

        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            # Clean up the tag text (remove extra whitespace and newlines)
            tag = re.sub(r"\s+", " ", match.strip())
            if tag and tag != "+":  # Skip the '+' button
                tags.append(tag)

        return tags

    def get_app_reviews(self, appid: int) -> dict | None:
        """Get review summary for an app"""
        self._rate_limit()

        # Try using the Steam API first
        try:
            # Note: python-steam-api doesn't have a direct method for reviews
            # So we'll make a direct API call
            url = f"https://store.steampowered.com/appreviews/{appid}"
            params = {"json": "1", "language": "all", "purchase_type": "all", "num_per_page": "0"}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if "query_summary" in data:
                    return data["query_summary"]
            else:
                logger.debug(f"Review API returned {response.status_code} for appid {appid}")

        except Exception as e:
            logger.debug(f"Error fetching reviews for {appid}: {e}")

        return None

    def get_player_summaries(self, steam_ids: str) -> list[dict]:
        """Get player profile information from Steam API (supports single ID or comma-separated list)"""
        logger.info(f"Fetching player profile(s) for Steam ID(s): {steam_ids}")

        try:
            url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            params = {"key": self.api_key, "steamids": steam_ids, "format": "json"}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if "response" in data and "players" in data["response"]:
                    return data["response"]["players"]
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

    def get_player_badges(self, steam_id: str) -> dict | None:
        """Get player badges and XP information from Steam API"""
        logger.info(f"Fetching player badges/XP for Steam ID: {steam_id}")

        try:
            url = "http://api.steampowered.com/IPlayerService/GetBadges/v1/"
            params = {"key": self.api_key, "steamid": steam_id, "format": "json"}  # Note: singular 'steamid', not 'steamids'

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if "response" in data:
                    return data["response"]
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

    def get_friend_list(self, steam_id: str) -> list[dict]:
        """Get friend list from Steam API"""
        logger.info(f"Fetching friend list for Steam ID: {steam_id}")

        try:
            url = "http://api.steampowered.com/ISteamUser/GetFriendList/v0001/"
            params = {"key": self.api_key, "steamid": steam_id, "relationship": "friend", "format": "json"}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if "friendslist" in data and "friends" in data["friendslist"]:
                    friends = data["friendslist"]["friends"]
                    logger.info(f"Found {len(friends)} friends")
                    return friends
                else:
                    logger.error("No friends found in response")
                    return []
            elif response.status_code == 401:
                logger.error("Unauthorized - check your API key")
                return []
            else:
                logger.error(f"Steam API returned {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error fetching friend list: {e}")
            return []

    def save_user_profile(self, player_data: dict | None, steam_id: str, include_badges: bool = False):
        """Save or update a user profile (reusable for main user and friends)

        Args:
            player_data: Player data from Steam API (None if API call failed)
            steam_id: Steam ID to save
            include_badges: Whether to fetch and save XP/level data (only for main user)
        """
        with get_db_transaction() as session:
            user = session.query(UserProfile).filter_by(steam_id=steam_id).first()

            if player_data:
                # Extract profile data from API response
                persona_name = player_data.get("personaname", "")
                profile_url = player_data.get("profileurl", "")
                avatar = player_data.get("avatar", "")
                avatarmedium = player_data.get("avatarmedium", "")
                avatarfull = player_data.get("avatarfull", "")
                time_created = player_data.get("timecreated", 0)
                loccountrycode = player_data.get("loccountrycode", "")
                locstatecode = player_data.get("locstatecode", "")

                # Get XP and level data only for main user
                xp = 0
                steam_level = 0
                if include_badges:
                    badges_data = self.get_player_badges(steam_id)
                    if badges_data:
                        xp = badges_data.get("player_xp", 0)
                        steam_level = badges_data.get("player_level", 0)
                        logger.info(f"Player XP: {xp}, Level: {steam_level}")

                if not user:
                    user = UserProfile(steam_id=steam_id, persona_name=persona_name, profile_url=profile_url, avatar_url=avatar, avatarmedium=avatarmedium, avatarfull=avatarfull, time_created=time_created, loccountrycode=loccountrycode, locstatecode=locstatecode, xp=xp, steam_level=steam_level, last_updated=int(datetime.now().timestamp()))
                    session.add(user)
                    logger.info(f"Created user profile for: {persona_name} (Steam ID: {steam_id})")
                else:
                    # Update existing user profile
                    user.persona_name = persona_name
                    user.profile_url = profile_url
                    user.avatar_url = avatar
                    user.avatarmedium = avatarmedium
                    user.avatarfull = avatarfull
                    user.time_created = time_created
                    user.loccountrycode = loccountrycode
                    user.locstatecode = locstatecode
                    if include_badges:
                        user.xp = xp
                        user.steam_level = steam_level
                    user.last_updated = int(datetime.now().timestamp())
                    logger.info(f"Updated user profile for: {persona_name} (Steam ID: {steam_id})")

            else:
                # Create minimal profile if API call failed
                if not user:
                    user = UserProfile(steam_id=steam_id, last_updated=int(datetime.now().timestamp()))
                    session.add(user)
                    logger.info(f"Created minimal user profile for Steam ID: {steam_id}")

    def process_game(self, game: dict, index: int, total: int) -> dict:
        """Process a single game and gather all required information"""
        appid = game.get("appid")
        name = game.get("name", "Unknown")

        # Check if we should skip games entirely
        if self.skip_games:
            logger.debug(f"Skipping game details for {name} (--skip-games flag)")
            return {"appid": appid, "name": name, "playtime_forever": game.get("playtime_forever", 0), "playtime_2weeks": game.get("playtime_2weeks", 0), "skip_details": True}

        # Check if data is fresh enough to skip API calls
        if self._is_game_cached(appid):
            logger.info(f"Processing [{index}/{total}]: {name} (AppID: {appid}) - Using cached data")
            # Return minimal data - the save_to_database will only update playtime
            return {"appid": appid, "name": name, "playtime_forever": game.get("playtime_forever", 0), "playtime_2weeks": game.get("playtime_2weeks", 0), "skip_details": True}

        # Progress indicator
        logger.info(f"Processing [{index}/{total}]: {name} (AppID: {appid}) - Fetching fresh data")

        game_info = {"appid": appid, "name": name, "playtime_forever": game.get("playtime_forever", 0), "playtime_2weeks": game.get("playtime_2weeks", 0), "required_age": 0, "short_description": "", "detailed_description": "", "about_the_game": "", "recommendations_total": 0, "metacritic_score": 0, "metacritic_url": "", "header_image": "", "platforms_windows": False, "platforms_mac": False, "platforms_linux": False, "controller_support": "", "vr_support": False, "esrb_rating": "", "esrb_descriptors": "", "pegi_rating": "", "pegi_descriptors": "", "genres": "", "categories": "", "developers": "", "publishers": "", "release_date": "", "tags": "", "review_summary": "Unknown", "review_score": 0, "total_reviews": 0, "positive_reviews": 0, "negative_reviews": 0}

        # Get detailed app information
        app_details = self.get_app_details(appid)
        if app_details:
            # Required age (directly from API)
            try:
                game_info["required_age"] = int(app_details.get("required_age", 0))
            except (ValueError, TypeError):
                game_info["required_age"] = 0

            # Short description
            game_info["short_description"] = app_details.get("short_description", "")

            # Detailed description
            game_info["detailed_description"] = app_details.get("detailed_description", "")

            # About the game
            game_info["about_the_game"] = app_details.get("about_the_game", "")

            # Recommendations total - handle None values
            recommendations = app_details.get("recommendations") or {}
            try:
                game_info["recommendations_total"] = int(recommendations.get("total", 0))
            except (ValueError, TypeError):
                game_info["recommendations_total"] = 0

            # Metacritic data - handle None values
            metacritic = app_details.get("metacritic") or {}
            try:
                game_info["metacritic_score"] = int(metacritic.get("score", 0))
            except (ValueError, TypeError):
                game_info["metacritic_score"] = 0
            game_info["metacritic_url"] = metacritic.get("url", "")

            # Header image
            game_info["header_image"] = app_details.get("header_image", "")

            # Platforms - handle None values
            platforms = app_details.get("platforms") or {}
            game_info["platforms_windows"] = platforms.get("windows", False)
            game_info["platforms_mac"] = platforms.get("mac", False)
            game_info["platforms_linux"] = platforms.get("linux", False)

            # Controller support
            game_info["controller_support"] = app_details.get("controller_support", "")

            # VR support (check categories for ID 31) - handle None values
            categories = app_details.get("categories") or []
            game_info["vr_support"] = any(cat.get("id") == 31 for cat in categories if cat)

            # ESRB rating - handle None values
            ratings = app_details.get("ratings") or {}
            esrb = ratings.get("esrb") or {}
            game_info["esrb_rating"] = esrb.get("rating", "")
            game_info["esrb_descriptors"] = esrb.get("descriptors", "")

            # PEGI rating - handle None values
            pegi = ratings.get("pegi") or {}
            game_info["pegi_rating"] = pegi.get("rating", "")
            game_info["pegi_descriptors"] = pegi.get("descriptors", "")

            # Genres - handle None values
            genres = app_details.get("genres") or []
            game_info["genres"] = ", ".join([g.get("description", "") for g in genres if g])

            # Categories (as string for existing functionality) - handle None values
            game_info["categories"] = ", ".join([c.get("description", "") for c in categories if c])

            # Developers and Publishers - handle None values
            game_info["developers"] = ", ".join(app_details.get("developers") or [])
            game_info["publishers"] = ", ".join(app_details.get("publishers") or [])

            # Release date - handle None values
            release_date = app_details.get("release_date") or {}
            game_info["release_date"] = release_date.get("date", "")

        # Get review information
        reviews = self.get_app_reviews(appid)
        if reviews:
            game_info["review_summary"] = reviews.get("review_score_desc", "Unknown")
            game_info["review_score"] = reviews.get("review_score", 0)
            game_info["total_reviews"] = reviews.get("total_reviews", 0)
            game_info["positive_reviews"] = reviews.get("total_positive", 0)
            game_info["negative_reviews"] = reviews.get("total_negative", 0)

        # Get user-generated tags
        tags = self.get_app_tags(appid)
        if tags:
            game_info["tags"] = ", ".join(tags[:20])  # Limit to first 20 tags
            logger.debug(f"Found {len(tags)} tags for {name}: {', '.join(tags[:5])}...")

        return game_info

    def save_to_database(self, game_data: dict, steam_id: str):
        """Save game data to SQLite database using SQLAlchemy"""
        with get_db_transaction() as session:
            app_id = game_data["appid"]
            skip_details = game_data.get("skip_details", False)

            # Create or update game
            game = session.query(Game).filter_by(app_id=app_id).first()
            if not game:
                game = Game(app_id=app_id, name=game_data["name"], required_age=game_data.get("required_age", 0), short_description=game_data.get("short_description", ""), detailed_description=game_data.get("detailed_description", ""), about_the_game=game_data.get("about_the_game", ""), recommendations_total=game_data.get("recommendations_total", 0), metacritic_score=game_data.get("metacritic_score", 0), metacritic_url=game_data.get("metacritic_url", ""), header_image=game_data.get("header_image", ""), platforms_windows=game_data.get("platforms_windows", False), platforms_mac=game_data.get("platforms_mac", False), platforms_linux=game_data.get("platforms_linux", False), controller_support=game_data.get("controller_support", ""), vr_support=game_data.get("vr_support", False), esrb_rating=game_data.get("esrb_rating", ""), esrb_descriptors=game_data.get("esrb_descriptors", ""), pegi_rating=game_data.get("pegi_rating", ""), pegi_descriptors=game_data.get("pegi_descriptors", ""), release_date=game_data.get("release_date", ""), last_updated=int(datetime.now().timestamp()) if not skip_details else None)
                session.add(game)
                session.flush()
            elif not skip_details:
                # Update existing game data only if we have fresh details
                game.name = game_data["name"]
                game.required_age = game_data.get("required_age", 0)
                game.short_description = game_data.get("short_description", "")
                game.detailed_description = game_data.get("detailed_description", "")
                game.about_the_game = game_data.get("about_the_game", "")
                game.recommendations_total = game_data.get("recommendations_total", 0)
                game.metacritic_score = game_data.get("metacritic_score", 0)
                game.metacritic_url = game_data.get("metacritic_url", "")
                game.header_image = game_data.get("header_image", "")
                game.platforms_windows = game_data.get("platforms_windows", False)
                game.platforms_mac = game_data.get("platforms_mac", False)
                game.platforms_linux = game_data.get("platforms_linux", False)
                game.controller_support = game_data.get("controller_support", "")
                game.vr_support = game_data.get("vr_support", False)
                game.esrb_rating = game_data.get("esrb_rating", "")
                game.esrb_descriptors = game_data.get("esrb_descriptors", "")
                game.pegi_rating = game_data.get("pegi_rating", "")
                game.pegi_descriptors = game_data.get("pegi_descriptors", "")
                game.release_date = game_data.get("release_date", "")
                game.last_updated = int(datetime.now().timestamp())

            # Skip detailed updates if we're using skip_details
            if not skip_details:
                # Handle genres
                if game_data.get("genres"):
                    # Clear existing genres for this game
                    game.genres.clear()
                    for genre_name in game_data["genres"].split(", "):
                        if genre_name.strip():
                            genre = get_or_create(session, Genre, genre_name=genre_name.strip())
                            game.genres.append(genre)

                # Handle developers
                if game_data.get("developers"):
                    game.developers.clear()
                    for dev_name in game_data["developers"].split(", "):
                        if dev_name.strip():
                            developer = get_or_create(session, Developer, developer_name=dev_name.strip())
                            game.developers.append(developer)

                # Handle publishers
                if game_data.get("publishers"):
                    game.publishers.clear()
                    for pub_name in game_data["publishers"].split(", "):
                        if pub_name.strip():
                            publisher = get_or_create(session, Publisher, publisher_name=pub_name.strip())
                            game.publishers.append(publisher)

                # Handle categories
                if game_data.get("categories"):
                    game.categories.clear()
                    for cat_name in game_data["categories"].split(", "):
                        if cat_name.strip():
                            category = get_or_create(session, Category, category_name=cat_name.strip())
                            game.categories.append(category)

                # Handle tags
                if game_data.get("tags"):
                    game.tags.clear()
                    for tag_name in game_data["tags"].split(", "):
                        if tag_name.strip():
                            tag = get_or_create(session, Tag, tag_name=tag_name.strip())
                            game.tags.append(tag)

                # Handle reviews
                if game_data.get("review_summary", "Unknown") != "Unknown" or game_data.get("total_reviews", 0) > 0:
                    review = session.query(GameReview).filter_by(app_id=app_id).first()
                    if not review:
                        review = GameReview(app_id=app_id, review_summary=game_data.get("review_summary", "Unknown"), review_score=game_data.get("review_score", 0), total_reviews=game_data.get("total_reviews", 0), positive_reviews=game_data.get("positive_reviews", 0), negative_reviews=game_data.get("negative_reviews", 0), last_updated=int(datetime.now().timestamp()))
                        session.add(review)
                    else:
                        # Update existing review
                        review.review_summary = game_data.get("review_summary", "Unknown")
                        review.review_score = game_data.get("review_score", 0)
                        review.total_reviews = game_data.get("total_reviews", 0)
                        review.positive_reviews = game_data.get("positive_reviews", 0)
                        review.negative_reviews = game_data.get("negative_reviews", 0)
                        review.last_updated = int(datetime.now().timestamp())

            # Handle user game data (always update this regardless of skip_details)
            user_game = session.query(UserGame).filter_by(steam_id=steam_id, app_id=app_id).first()

            if not user_game:
                user_game = UserGame(steam_id=steam_id, app_id=app_id, playtime_forever=game_data["playtime_forever"], playtime_2weeks=game_data["playtime_2weeks"])
                session.add(user_game)
            else:
                # Update playtime data
                user_game.playtime_forever = max(user_game.playtime_forever, game_data["playtime_forever"])
                user_game.playtime_2weeks = game_data["playtime_2weeks"]

    def fetch_library_data(self, steam_id: str):
        """Main method to fetch all library data and save to database"""
        # Create database tables if they don't exist
        create_database()

        # Create or update user profile (with XP/badges data for main user)
        player_profiles = self.get_player_summaries(steam_id)
        player_data = player_profiles[0] if player_profiles else None
        self.save_user_profile(player_data, steam_id, include_badges=True)

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
                fallback_data = {"appid": game.get("appid"), "name": game.get("name", "Unknown"), "playtime_forever": game.get("playtime_forever", 0), "playtime_2weeks": game.get("playtime_2weeks", 0), "required_age": 0, "short_description": "", "detailed_description": "", "about_the_game": "", "recommendations_total": 0, "metacritic_score": 0, "metacritic_url": "", "header_image": "", "platforms_windows": False, "platforms_mac": False, "platforms_linux": False, "controller_support": "", "vr_support": False, "esrb_rating": "", "esrb_descriptors": "", "pegi_rating": "", "pegi_descriptors": "", "genres": "", "categories": "", "developers": "", "publishers": "", "release_date": "", "review_summary": "Unknown", "review_score": 0, "total_reviews": 0, "positive_reviews": 0, "negative_reviews": 0}
                try:
                    self.save_to_database(fallback_data, steam_id)
                    processed_count += 1
                except Exception as db_error:
                    logger.error(f"Failed to save fallback data for {game.get('name', 'Unknown')}: {db_error}")

        if failed_count > 0:
            logger.warning(f"Note: {failed_count} games had limited data due to API restrictions")

        logger.info(f"Completed! Processed {processed_count} games successfully. Data saved to database")

        # Process friends if requested
        if self.fetch_friends:
            self.process_friends_data(steam_id)

    def process_friends_data(self, user_steam_id: str, batch_size: int = 100):
        """Fetch and process friends list and their games"""
        logger.info("\n" + "=" * 60)
        logger.info("Starting friends data processing...")
        logger.info("=" * 60 + "\n")

        # Get friend list
        friends = self.get_friend_list(user_steam_id)
        if not friends:
            logger.warning("No friends found or profile is private")
            return

        logger.info(f"Processing {len(friends)} friends...")

        # Save friend relationships
        self._save_friend_relationships(user_steam_id, friends)

        # Process friends' profiles and games in batches
        friend_ids = [f.get("steamid") for f in friends]
        self._process_friends_in_batches(friend_ids, batch_size)

        logger.info("\nFriends data processing completed!")

    def _save_friend_relationships(self, user_steam_id: str, friends: list[dict]):
        """Save friend relationships to database using association table"""
        with get_db_transaction() as session:
            for friend_data in friends:
                friend_steam_id = friend_data.get("steamid")
                relationship = friend_data.get("relationship", "friend")
                friend_since = friend_data.get("friend_since", 0)

                # Check if friend relationship already exists
                existing_friend = session.execute(friends_association.select().where((friends_association.c.user_steam_id == user_steam_id) & (friends_association.c.friend_steam_id == friend_steam_id))).first()

                if not existing_friend:
                    session.execute(friends_association.insert().values(user_steam_id=user_steam_id, friend_steam_id=friend_steam_id, relationship=relationship, friend_since=friend_since))

    def _process_friends_in_batches(self, friend_ids: list[str], batch_size: int):
        """Process friends' profiles and games in configurable batches"""
        for i in range(0, len(friend_ids), batch_size):
            batch = friend_ids[i : i + batch_size]
            batch_str = ",".join(batch)

            logger.info(f"Fetching profiles for batch {i//batch_size + 1}/{(len(friend_ids) + batch_size - 1)//batch_size}")

            # Get player summaries for batch - reuses existing method
            friend_profiles = self.get_player_summaries(batch_str)

            # Process each friend's profile and games
            for profile in friend_profiles:
                friend_steam_id = profile.get("steamid")
                visibility = profile.get("communityvisibilitystate", 1)

                # Only process friends with public profiles (visibility = 3)
                if visibility == 3:
                    logger.info(f"Processing friend: {profile.get('personaname', 'Unknown')} (Steam ID: {friend_steam_id})")

                    # Save friend's profile - reuses existing method without badges
                    self.save_user_profile(profile, friend_steam_id, include_badges=False)

                    # Fetch and save friend's games - reuses existing methods
                    friend_games = self.get_owned_games(friend_steam_id)
                    if friend_games:
                        logger.info(f"  Found {len(friend_games)} games for {profile.get('personaname')}")

                        # Process games using existing logic with caching
                        for game in friend_games:
                            try:
                                # Reuse existing process_game method with caching
                                game_data = self.process_game(game, 1, 1)  # Don't show progress for friends
                                # Reuse existing save_to_database method
                                self.save_to_database(game_data, friend_steam_id)
                            except Exception as e:
                                logger.debug(f"  Error processing game {game.get('name', 'Unknown')} for friend: {e}")
                else:
                    logger.info(f"Skipping friend with private profile: Steam ID {friend_steam_id}")


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Setup argument parser
    parser = argparse.ArgumentParser(description="Fetch Steam library data with caching support")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--cache-days", type=int, default=7, help="Maximum age in days before re-fetching game data (default: 7)")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh all game data, ignoring cache")
    parser.add_argument("--skip-games", action="store_true", help="Skip fetching game details entirely")
    parser.add_argument("--friends", action="store_true", help="Also fetch friends list and their game libraries")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Log version information
    logger.info(f"Steam Library Fetcher v{__version__} starting...")

    # Get environment variables (support both .env and env vars)
    steam_id = os.getenv("STEAM_ID")
    api_key = os.getenv("STEAM_API_KEY")

    # Also check for CACHE_DAYS env var
    cache_days = int(os.getenv("CACHE_DAYS", args.cache_days))

    if not steam_id or not api_key:
        logger.error("Missing environment variables!")
        logger.error("Please set STEAM_ID and STEAM_API_KEY in your .env file")
        sys.exit(1)

    logger.info(f"Starting Steam Library Fetcher for Steam ID: {steam_id}")
    if args.force_refresh:
        logger.info("Force refresh enabled - all game data will be re-fetched")
    else:
        logger.info(f"Using cache threshold of {cache_days} days")

    # Create fetcher and run
    fetcher = SteamLibraryFetcher(api_key)
    fetcher.cache_days = cache_days
    fetcher.force_refresh = args.force_refresh
    fetcher.skip_games = args.skip_games
    fetcher.fetch_friends = args.friends

    fetcher.fetch_library_data(steam_id)


if __name__ == "__main__":
    main()
