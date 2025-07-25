"""User-related models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

from src.core.database import Base

# Association table for friends relationships
friends_association = Table(
    'friends',
    Base.metadata,
    Column('user_steam_id', String, ForeignKey('user_profile.steam_id'), primary_key=True),
    Column('friend_steam_id', String, ForeignKey('user_profile.steam_id'), primary_key=True),
    Column('relationship', String),  # 'friend' or 'all'
    Column('friend_since', Integer)  # Unix timestamp
)


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
    friends = relationship(
        "UserProfile",
        secondary=friends_association,
        primaryjoin=steam_id == friends_association.c.user_steam_id,
        secondaryjoin=steam_id == friends_association.c.friend_steam_id,
        back_populates="friend_of"
    )
    friend_of = relationship(
        "UserProfile", 
        secondary=friends_association,
        primaryjoin=steam_id == friends_association.c.friend_steam_id,
        secondaryjoin=steam_id == friends_association.c.user_steam_id,
        back_populates="friends"
    )


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