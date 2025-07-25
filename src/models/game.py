"""Game-related models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from src.core.database import Base

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