"""Review-related models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from src.core.database import Base


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