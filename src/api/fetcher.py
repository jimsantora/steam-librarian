"""High-level Steam data fetching and orchestration logic"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.core.database import get_db, get_or_create
from src.models import (
    Game, UserGame, Genre, Developer, Publisher, Category, 
    GameReview, UserProfile, friends_association
)
from src.api.steam_client import SteamLibraryFetcher

logger = logging.getLogger(__name__)


class SteamDataFetcher:
    """High-level orchestrator for fetching and saving Steam data"""
    
    def __init__(self, steam_client: SteamLibraryFetcher):
        self.client = steam_client
        
    def save_user_profile(self, player_data: Optional[Dict], steam_id: str, include_badges: bool = False):
        """Save or update a user profile (reusable for main user and friends)
        
        Args:
            player_data: Player data from Steam API (None if API call failed)
            steam_id: Steam ID to save
            include_badges: Whether to fetch and save XP/level data (only for main user)
        """
        with get_db() as session:
            user = session.query(UserProfile).filter_by(steam_id=steam_id).first()
            
            if player_data:
                # Extract profile data from API response
                persona_name = player_data.get('personaname', '')
                profile_url = player_data.get('profileurl', '')
                avatar = player_data.get('avatar', '')
                avatarmedium = player_data.get('avatarmedium', '')
                avatarfull = player_data.get('avatarfull', '')
                time_created = player_data.get('timecreated', 0)
                loccountrycode = player_data.get('loccountrycode', '')
                locstatecode = player_data.get('locstatecode', '')
                
                # Get XP and level data only for main user
                xp = 0
                steam_level = 0
                if include_badges:
                    badges_data = self.client.get_player_badges(steam_id)
                    if badges_data:
                        xp = badges_data.get('player_xp', 0)
                        steam_level = badges_data.get('player_level', 0)
                        logger.info(f"Player XP: {xp}, Level: {steam_level}")
                
                if not user:
                    user = UserProfile(
                        steam_id=steam_id,
                        persona_name=persona_name,
                        profile_url=profile_url,
                        avatar_url=avatar,
                        avatarmedium=avatarmedium,
                        avatarfull=avatarfull,
                        time_created=time_created,
                        account_created=time_created,  # For backwards compatibility
                        loccountrycode=loccountrycode,
                        locstatecode=locstatecode,
                        xp=xp,
                        steam_level=steam_level,
                        last_updated=int(datetime.now().timestamp())
                    )
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
                    user.account_created = time_created  # For backwards compatibility
                    user.loccountrycode = loccountrycode
                    user.locstatecode = locstatecode
                    if include_badges:
                        user.xp = xp
                        user.steam_level = steam_level
                    user.last_updated = int(datetime.now().timestamp())
                    logger.info(f"Updated user profile for: {persona_name} (Steam ID: {steam_id})")
                
                session.commit()
            else:
                # Create minimal profile if API call failed
                if not user:
                    user = UserProfile(
                        steam_id=steam_id,
                        last_updated=int(datetime.now().timestamp())
                    )
                    session.add(user)
                    session.commit()
                    logger.info(f"Created minimal user profile for Steam ID: {steam_id}")
        
    def process_game(self, game: Dict, index: int, total: int) -> Dict:
        """Process a single game and gather all required information"""
        appid = game.get('appid')
        name = game.get('name', 'Unknown')
        
        # Check if we should skip games entirely
        if self.client.skip_games:
            logger.debug(f"Skipping game details for {name} (--skip-games flag)")
            return {
                'appid': appid,
                'name': name,
                'playtime_forever': game.get('playtime_forever', 0),
                'playtime_2weeks': game.get('playtime_2weeks', 0),
                'skip_details': True
            }
        
        # Check if data is fresh enough to skip API calls
        if self.client._is_game_cached(appid):
            logger.info(f"Processing [{index}/{total}]: {name} (AppID: {appid}) - Using cached data")
            # Return minimal data - the save_to_database will only update playtime
            return {
                'appid': appid,
                'name': name,
                'playtime_forever': game.get('playtime_forever', 0),
                'playtime_2weeks': game.get('playtime_2weeks', 0),
                'skip_details': True
            }
        
        # Progress indicator
        logger.info(f"Processing [{index}/{total}]: {name} (AppID: {appid}) - Fetching fresh data")
        
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
        app_details = self.client.get_app_details(appid)
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
        reviews = self.client.get_app_reviews(appid)
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
            skip_details = game_data.get('skip_details', False)
            
            # Create or update game
            game = session.query(Game).filter_by(app_id=app_id).first()
            if not game:
                game = Game(
                    app_id=app_id,
                    name=game_data['name'],
                    maturity_rating=game_data.get('maturity_rating'),
                    required_age=game_data.get('required_age', 0),
                    content_descriptors=game_data.get('content_descriptors'),
                    release_date=game_data.get('release_date'),
                    last_updated=int(datetime.now().timestamp())
                )
                session.add(game)
            elif not skip_details:
                # Update game details only if we fetched fresh data
                game.name = game_data['name']
                game.maturity_rating = game_data.get('maturity_rating')
                game.required_age = game_data.get('required_age', 0)
                game.content_descriptors = game_data.get('content_descriptors')
                game.release_date = game_data.get('release_date')
                game.last_updated = int(datetime.now().timestamp())
            
            # Handle genres (many-to-many)
            if 'genres' in game_data and game_data['genres'] and not skip_details:
                game.genres.clear()  # Clear existing genres
                for genre_name in game_data['genres'].split(', '):
                    if genre_name:
                        genre = get_or_create(session, Genre, genre_name=genre_name)
                        game.genres.append(genre)
            
            # Handle categories (many-to-many)
            if 'categories' in game_data and game_data['categories'] and not skip_details:
                game.categories.clear()  # Clear existing categories
                for category_name in game_data['categories'].split(', '):
                    if category_name:
                        category = get_or_create(session, Category, category_name=category_name)
                        game.categories.append(category)
            
            # Handle developers (many-to-many)
            if 'developers' in game_data and game_data['developers'] and not skip_details:
                game.developers.clear()  # Clear existing developers
                for dev_name in game_data['developers'].split(', '):
                    if dev_name:
                        developer = get_or_create(session, Developer, developer_name=dev_name)
                        game.developers.append(developer)
            
            # Handle publishers (many-to-many)
            if 'publishers' in game_data and game_data['publishers'] and not skip_details:
                game.publishers.clear()  # Clear existing publishers
                for pub_name in game_data['publishers'].split(', '):
                    if pub_name:
                        publisher = get_or_create(session, Publisher, publisher_name=pub_name)
                        game.publishers.append(publisher)
            
            # Create or update user-game relationship
            user_game = session.query(UserGame).filter_by(
                steam_id=steam_id, 
                app_id=app_id
            ).first()
            
            if not user_game:
                user_game = UserGame(
                    steam_id=steam_id,
                    app_id=app_id,
                    playtime_forever=game_data['playtime_forever'],
                    playtime_2weeks=game_data.get('playtime_2weeks', 0)
                )
                session.add(user_game)
            else:
                # Always update playtime (even for cached games)
                user_game.playtime_forever = game_data['playtime_forever']
                user_game.playtime_2weeks = game_data.get('playtime_2weeks', 0)
            
            # Create or update review data
            if not skip_details and game_data.get('total_reviews', 0) > 0:
                review = session.query(GameReview).filter_by(app_id=app_id).first()
                if not review:
                    review = GameReview(
                        app_id=app_id,
                        review_summary=game_data.get('review_summary', 'Unknown'),
                        review_score=game_data.get('review_score', 0),
                        total_reviews=game_data.get('total_reviews', 0),
                        positive_reviews=game_data.get('positive_reviews', 0),
                        negative_reviews=game_data.get('negative_reviews', 0),
                        last_updated=int(datetime.now().timestamp())
                    )
                    session.add(review)
                else:
                    review.review_summary = game_data.get('review_summary', 'Unknown')
                    review.review_score = game_data.get('review_score', 0)
                    review.total_reviews = game_data.get('total_reviews', 0)
                    review.positive_reviews = game_data.get('positive_reviews', 0)
                    review.negative_reviews = game_data.get('negative_reviews', 0)
                    review.last_updated = int(datetime.now().timestamp())
            
            session.commit()
            
    def fetch_friends_data(self, steam_id: str):
        """Fetch and save friends list for a user"""
        logger.info(f"Fetching friends for user {steam_id}...")
        
        # Get friend list
        friends = self.client.get_friend_list(steam_id)
        if not friends:
            logger.info("No friends found or friend list is private")
            return
        
        logger.info(f"Found {len(friends)} friends")
        
        # Get friend steam IDs
        friend_steam_ids = [friend['steamid'] for friend in friends]
        
        # Fetch all friend profiles in one API call (up to 100 at a time)
        all_friend_profiles = []
        for i in range(0, len(friend_steam_ids), 100):
            batch = friend_steam_ids[i:i+100]
            batch_ids = ','.join(batch)
            profiles = self.client.get_player_summaries(batch_ids)
            all_friend_profiles.extend(profiles)
        
        # Save friend profiles
        for profile in all_friend_profiles:
            self.save_user_profile(profile, profile['steamid'], include_badges=False)
        
        # Save friend relationships
        with get_db() as session:
            # Get the user to ensure they exist
            user = session.query(UserProfile).filter_by(steam_id=steam_id).first()
            if not user:
                logger.error(f"User {steam_id} not found in database")
                return
            
            # Clear existing friend relationships for this user
            session.execute(
                friends_association.delete().where(
                    friends_association.c.user_steam_id == steam_id
                )
            )
            
            # Add new friend relationships
            for friend in friends:
                friend_steam_id = friend['steamid']
                relationship = friend.get('relationship', 'friend')
                friend_since = friend.get('friend_since', 0)
                
                # Insert the relationship
                session.execute(
                    friends_association.insert().values(
                        user_steam_id=steam_id,
                        friend_steam_id=friend_steam_id,
                        relationship=relationship,
                        friend_since=friend_since
                    )
                )
            
            session.commit()
            logger.info(f"Saved {len(friends)} friend relationships")
    
    def run(self, steam_id: str):
        """Main method to fetch all Steam library data"""
        logger.info(f"Starting Steam library fetch for user {steam_id}")
        
        # Fetch and save user profile first (with XP/level data)
        logger.info("Fetching user profile...")
        player_summaries = self.client.get_player_summaries(steam_id)
        if player_summaries:
            self.save_user_profile(player_summaries[0], steam_id, include_badges=True)
        else:
            logger.warning("Could not fetch user profile data")
            # Create minimal profile to continue
            self.save_user_profile(None, steam_id)
        
        # Fetch owned games unless skip_games is set
        if not self.client.skip_games:
            games = self.client.get_owned_games(steam_id)
            
            if not games:
                logger.error("No games found. Please check your Steam ID and API key.")
                return
            
            logger.info(f"Found {len(games)} games in library")
            
            # Process each game
            for index, game in enumerate(games, 1):
                try:
                    game_data = self.process_game(game, index, len(games))
                    self.save_to_database(game_data, steam_id)
                except Exception as e:
                    logger.error(f"Error processing game {game.get('name', 'Unknown')}: {e}")
                    continue
        else:
            logger.info("Skipping game library fetch (--skip-games flag)")
        
        # Fetch friends data if requested
        if self.client.fetch_friends:
            self.fetch_friends_data(steam_id)
        
        logger.info("Steam library data fetch complete!")