import logging
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.exc import DisconnectionError, StatementError, TimeoutError
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()

# Get database URL from environment or construct default
default_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "steam_library.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}")

# Create engine with performance optimizations
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
        "timeout": 30,
    },
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def db_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for database operations with exponential backoff retry logic"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (DisconnectionError, TimeoutError, StatementError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Database operation failed after {max_retries + 1} attempts: {e}")
                        raise e

                    # Exponential backoff with jitter
                    delay = base_delay * (2**attempt) + (time.time() % 1)  # Add jitter
                    logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                except Exception as e:
                    # Don't retry non-connection errors
                    raise e

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
@db_retry(max_retries=3, base_delay=1.0)
def get_db_transaction():
    """Context manager for database sessions with transaction management and retry logic"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# Association tables for many-to-many relationships
game_genres = Table("game_genres", Base.metadata, Column("app_id", Integer, ForeignKey("games.app_id"), primary_key=True), Column("genre_id", Integer, ForeignKey("genres.genre_id"), primary_key=True))

game_developers = Table("game_developers", Base.metadata, Column("app_id", Integer, ForeignKey("games.app_id"), primary_key=True), Column("developer_id", Integer, ForeignKey("developers.developer_id"), primary_key=True))

game_publishers = Table("game_publishers", Base.metadata, Column("app_id", Integer, ForeignKey("games.app_id"), primary_key=True), Column("publisher_id", Integer, ForeignKey("publishers.publisher_id"), primary_key=True))

game_categories = Table("game_categories", Base.metadata, Column("app_id", Integer, ForeignKey("games.app_id"), primary_key=True), Column("category_id", Integer, ForeignKey("categories.category_id"), primary_key=True))

# Association table for friends relationships
friends_association = Table("friends", Base.metadata, Column("user_steam_id", String, ForeignKey("user_profile.steam_id"), primary_key=True), Column("friend_steam_id", String, ForeignKey("user_profile.steam_id"), primary_key=True), Column("relationship", String), Column("friend_since", Integer), Index("idx_friends_user_steam_id", "user_steam_id"), Index("idx_friends_friend_steam_id", "friend_steam_id"))  # 'friend' or 'all'  # Unix timestamp


# Models
class UserProfile(Base):
    __tablename__ = "user_profile"

    steam_id = Column(String, primary_key=True)
    persona_name = Column(String)
    profile_url = Column(String)
    avatar_url = Column(String)  # Small avatar
    avatarmedium = Column(String)  # Medium avatar URL
    avatarfull = Column(String)  # Full avatar URL
    time_created = Column(Integer)  # Account creation timestamp
    loccountrycode = Column(String)  # Country code (e.g., "US")
    locstatecode = Column(String)  # State/region code (e.g., "CA")
    xp = Column(Integer)  # Raw XP value
    steam_level = Column(Integer)  # Calculated from XP
    last_updated = Column(Integer, default=lambda: int(datetime.now().timestamp()))

    # Relationships
    games = relationship("UserGame", back_populates="user", cascade="all, delete-orphan")
    friends = relationship("UserProfile", secondary=friends_association, primaryjoin=steam_id == friends_association.c.user_steam_id, secondaryjoin=steam_id == friends_association.c.friend_steam_id, back_populates="friend_of")
    friend_of = relationship("UserProfile", secondary=friends_association, primaryjoin=steam_id == friends_association.c.friend_steam_id, secondaryjoin=steam_id == friends_association.c.user_steam_id, back_populates="friends")


class Game(Base):
    __tablename__ = "games"

    app_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    required_age = Column(Integer, default=0)
    short_description = Column(Text)
    detailed_description = Column(Text)
    about_the_game = Column(Text)
    recommendations_total = Column(Integer)
    metacritic_score = Column(Integer)
    metacritic_url = Column(String)
    header_image = Column(String)
    platforms_windows = Column(Boolean, default=False)
    platforms_mac = Column(Boolean, default=False)
    platforms_linux = Column(Boolean, default=False)
    controller_support = Column(String)
    vr_support = Column(Boolean, default=False)
    esrb_rating = Column(String)
    esrb_descriptors = Column(Text)
    pegi_rating = Column(String)
    pegi_descriptors = Column(Text)
    release_date = Column(String)
    last_updated = Column(Integer, default=lambda: int(datetime.now().timestamp()))

    # Relationships
    users = relationship("UserGame", back_populates="game", cascade="all, delete-orphan")
    reviews = relationship("GameReview", back_populates="game", uselist=False, cascade="all, delete-orphan")
    genres = relationship("Genre", secondary=game_genres, back_populates="games")
    developers = relationship("Developer", secondary=game_developers, back_populates="games")
    publishers = relationship("Publisher", secondary=game_publishers, back_populates="games")
    categories = relationship("Category", secondary=game_categories, back_populates="games")

    # Indexes for search and filtering
    __table_args__ = (
        Index("idx_games_name", "name"),
        Index("idx_games_esrb_rating", "esrb_rating"),
    )


class UserGame(Base):
    __tablename__ = "user_games"

    steam_id = Column(String, ForeignKey("user_profile.steam_id"), primary_key=True)
    app_id = Column(Integer, ForeignKey("games.app_id"), primary_key=True)
    playtime_forever = Column(Integer, default=0)  # in minutes
    playtime_2weeks = Column(Integer, default=0)  # in minutes

    # Relationships
    user = relationship("UserProfile", back_populates="games")
    game = relationship("Game", back_populates="users")

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_user_games_steam_id", "steam_id"),
        Index("idx_user_games_app_id", "app_id"),
        Index("idx_user_games_playtime_forever", "playtime_forever"),
        Index("idx_user_games_playtime_2weeks", "playtime_2weeks"),
    )

    @property
    def playtime_hours(self):
        """Convert playtime from minutes to hours"""
        return round(self.playtime_forever / 60, 1) if self.playtime_forever else 0

    @property
    def playtime_2weeks_hours(self):
        """Convert recent playtime from minutes to hours"""
        return round(self.playtime_2weeks / 60, 1) if self.playtime_2weeks else 0


class Genre(Base):
    __tablename__ = "genres"

    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    genre_name = Column(String, unique=True, nullable=False)

    # Relationships
    games = relationship("Game", secondary=game_genres, back_populates="genres")


class Developer(Base):
    __tablename__ = "developers"

    developer_id = Column(Integer, primary_key=True, autoincrement=True)
    developer_name = Column(String, unique=True, nullable=False)

    # Relationships
    games = relationship("Game", secondary=game_developers, back_populates="developers")


class Publisher(Base):
    __tablename__ = "publishers"

    publisher_id = Column(Integer, primary_key=True, autoincrement=True)
    publisher_name = Column(String, unique=True, nullable=False)

    # Relationships
    games = relationship("Game", secondary=game_publishers, back_populates="publishers")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, unique=True, nullable=False)

    # Relationships
    games = relationship("Game", secondary=game_categories, back_populates="categories")


class GameReview(Base):
    __tablename__ = "game_reviews"

    app_id = Column(Integer, ForeignKey("games.app_id"), primary_key=True)
    review_summary = Column(String)
    review_score = Column(Integer)
    total_reviews = Column(Integer, default=0)
    positive_reviews = Column(Integer, default=0)
    negative_reviews = Column(Integer, default=0)
    last_updated = Column(Integer, default=lambda: int(datetime.now().timestamp()))

    # Relationships
    game = relationship("Game", back_populates="reviews")

    @property
    def positive_percentage(self):
        """Calculate positive review percentage"""
        if self.total_reviews > 0:
            return round((self.positive_reviews / self.total_reviews) * 100, 1)
        return 0


def create_database():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def drop_database():
    """Drop all tables in the database"""
    Base.metadata.drop_all(bind=engine)


# Helper functions for common queries
def get_or_create(session: Session, model, **kwargs):
    """Get an existing instance or create a new one"""
    instance = session.query(model).filter_by(**kwargs).first()
    if not instance:
        instance = model(**kwargs)
        session.add(instance)
    return instance


def bulk_insert_or_update(session: Session, model, data_list, unique_fields):
    """Efficiently insert or update multiple records"""
    for data in data_list:
        filters = {field: data[field] for field in unique_fields if field in data}
        instance = session.query(model).filter_by(**filters).first()

        if instance:
            # Update existing
            for key, value in data.items():
                setattr(instance, key, value)
        else:
            # Insert new
            instance = model(**data)
            session.add(instance)

    session.commit()


# Error handling utilities
def create_error_response(error_type: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a standardized error response format"""
    response = {"error": True, "error_type": error_type, "message": message}
    if details:
        response["details"] = details
    return response


def create_success_response(data: Any, message: str | None = None) -> dict[str, Any]:
    """Create a standardized success response format"""
    response = {"error": False, "data": data}
    if message:
        response["message"] = message
    return response


def handle_user_not_found(user_identifier: str) -> dict[str, Any]:
    """Standard response for user not found scenarios"""
    return create_error_response("USER_NOT_FOUND", f"User not found: {user_identifier}. Use get_all_users() to see available users.", {"user_identifier": user_identifier})


def handle_game_not_found(game_identifier: str) -> dict[str, Any]:
    """Standard response for game not found scenarios"""
    return create_error_response("GAME_NOT_FOUND", f"Game not found: {game_identifier}", {"game_identifier": game_identifier})


def handle_multiple_users(users: list) -> dict[str, Any]:
    """Standard response for multiple users scenario"""
    return create_error_response("MULTIPLE_USERS_FOUND", "Multiple users found. Please specify which user by Steam ID or persona name.", {"available_users": [{"steam_id": user.steam_id, "persona_name": user.persona_name or "Unknown"} for user in users]})


def resolve_user_identifier(user_identifier: str, session: Session | None = None) -> str | None:
    """Resolve a user identifier (Steam ID or persona name) to a Steam ID"""
    if not user_identifier:
        return None

    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        # First, try exact Steam ID match
        user = session.query(UserProfile).filter_by(steam_id=user_identifier).first()
        if user:
            return user.steam_id

        # Then try case-insensitive persona name match
        user = session.query(UserProfile).filter(func.lower(UserProfile.persona_name) == func.lower(user_identifier)).first()
        if user:
            return user.steam_id

        return None
    finally:
        if close_session:
            session.close()


def resolve_user_for_tool(user_steam_id: str | None = None, get_user_steam_id_fallback: Callable[[], str] | None = None) -> dict[str, Any]:
    """
    Utility function to resolve user for MCP tools with consistent behavior.

    Args:
        user_steam_id: Optional Steam ID or persona name
        get_user_steam_id_fallback: Optional function to get Steam ID from environment

    Returns:
        Dict with either 'steam_id' key or 'error' key with error details
    """
    # Resolve user identifier if provided
    if user_steam_id:
        resolved_steam_id = resolve_user_identifier(user_steam_id)
        if not resolved_steam_id:
            return handle_user_not_found(user_steam_id)
        return {"steam_id": resolved_steam_id}

    # Auto-select user if none provided
    with get_db() as session:
        users = session.query(UserProfile).all()

        if len(users) == 1:
            return {"steam_id": users[0].steam_id}
        elif len(users) > 1:
            return handle_multiple_users(users)
        else:
            # No users in database, try fallback
            if get_user_steam_id_fallback:
                fallback_steam_id = get_user_steam_id_fallback()
                if fallback_steam_id:
                    return {"steam_id": fallback_steam_id}

            return create_error_response("NO_USERS_FOUND", "No users found in database. Please fetch Steam library data first.", {})
