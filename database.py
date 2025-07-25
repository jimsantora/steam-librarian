import os
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.sql import func

Base = declarative_base()

# Get database path from environment or use default
DB_PATH = os.environ.get('STEAM_LIBRARY_DB', 'steam_library.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with performance optimizations
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
        "timeout": 30,
    },
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Association tables for many-to-many relationships
game_genres = Table(
    'game_genres',
    Base.metadata,
    Column('app_id', Integer, ForeignKey('games.app_id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.genre_id'), primary_key=True)
)

game_developers = Table(
    'game_developers',
    Base.metadata,
    Column('app_id', Integer, ForeignKey('games.app_id'), primary_key=True),
    Column('developer_id', Integer, ForeignKey('developers.developer_id'), primary_key=True)
)

game_publishers = Table(
    'game_publishers',
    Base.metadata,
    Column('app_id', Integer, ForeignKey('games.app_id'), primary_key=True),
    Column('publisher_id', Integer, ForeignKey('publishers.publisher_id'), primary_key=True)
)

game_categories = Table(
    'game_categories',
    Base.metadata,
    Column('app_id', Integer, ForeignKey('games.app_id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.category_id'), primary_key=True)
)

# Models
class UserProfile(Base):
    __tablename__ = 'user_profile'
    
    steam_id = Column(String, primary_key=True)
    persona_name = Column(String)
    profile_url = Column(String)
    avatar_url = Column(String)  # Small avatar
    avatarmedium = Column(String)  # Medium avatar URL
    avatarfull = Column(String)  # Full avatar URL
    time_created = Column(Integer)  # Account creation timestamp
    account_created = Column(Integer)  # Deprecated - use time_created
    loccountrycode = Column(String)  # Country code (e.g., "US")
    locstatecode = Column(String)  # State/region code (e.g., "CA")
    xp = Column(Integer)  # Raw XP value
    steam_level = Column(Integer)  # Calculated from XP
    last_updated = Column(Integer, default=lambda: int(datetime.now().timestamp()))
    
    # Relationships
    games = relationship("UserGame", back_populates="user", cascade="all, delete-orphan")

class Game(Base):
    __tablename__ = 'games'
    
    app_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    maturity_rating = Column(String)
    required_age = Column(Integer, default=0)
    content_descriptors = Column(Text)
    release_date = Column(String)
    metacritic_score = Column(Integer)
    steam_deck_verified = Column(Boolean, default=False)
    controller_support = Column(String)
    vr_support = Column(Boolean, default=False)
    last_updated = Column(Integer, default=lambda: int(datetime.now().timestamp()))
    
    # Relationships
    users = relationship("UserGame", back_populates="game", cascade="all, delete-orphan")
    reviews = relationship("GameReview", back_populates="game", uselist=False, cascade="all, delete-orphan")
    genres = relationship("Genre", secondary=game_genres, back_populates="games")
    developers = relationship("Developer", secondary=game_developers, back_populates="games")
    publishers = relationship("Publisher", secondary=game_publishers, back_populates="games")
    categories = relationship("Category", secondary=game_categories, back_populates="games")

class UserGame(Base):
    __tablename__ = 'user_games'
    
    steam_id = Column(String, ForeignKey('user_profile.steam_id'), primary_key=True)
    app_id = Column(Integer, ForeignKey('games.app_id'), primary_key=True)
    playtime_forever = Column(Integer, default=0)  # in minutes
    playtime_2weeks = Column(Integer, default=0)   # in minutes
    last_played = Column(Integer)  # Unix timestamp
    purchase_date = Column(Integer)
    purchase_price = Column(Float)
    
    # Relationships
    user = relationship("UserProfile", back_populates="games")
    game = relationship("Game", back_populates="users")
    
    @property
    def playtime_hours(self):
        """Convert playtime from minutes to hours"""
        return round(self.playtime_forever / 60, 1) if self.playtime_forever else 0
    
    @property
    def playtime_2weeks_hours(self):
        """Convert recent playtime from minutes to hours"""
        return round(self.playtime_2weeks / 60, 1) if self.playtime_2weeks else 0

class Genre(Base):
    __tablename__ = 'genres'
    
    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    genre_name = Column(String, unique=True, nullable=False)
    
    # Relationships
    games = relationship("Game", secondary=game_genres, back_populates="genres")

class Developer(Base):
    __tablename__ = 'developers'
    
    developer_id = Column(Integer, primary_key=True, autoincrement=True)
    developer_name = Column(String, unique=True, nullable=False)
    
    # Relationships
    games = relationship("Game", secondary=game_developers, back_populates="developers")

class Publisher(Base):
    __tablename__ = 'publishers'
    
    publisher_id = Column(Integer, primary_key=True, autoincrement=True)
    publisher_name = Column(String, unique=True, nullable=False)
    
    # Relationships
    games = relationship("Game", secondary=game_publishers, back_populates="publishers")

class Category(Base):
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, unique=True, nullable=False)
    
    # Relationships
    games = relationship("Game", secondary=game_categories, back_populates="categories")

class GameReview(Base):
    __tablename__ = 'game_reviews'
    
    app_id = Column(Integer, ForeignKey('games.app_id'), primary_key=True)
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