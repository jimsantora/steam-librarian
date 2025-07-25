"""Models package"""
from src.models.game import Game, Genre, Developer, Publisher, Category, game_genres, game_developers, game_publishers, game_categories
from src.models.user import UserProfile, UserGame, friends_association
from src.models.review import GameReview

__all__ = [
    'Game', 'Genre', 'Developer', 'Publisher', 'Category',
    'UserProfile', 'UserGame', 'GameReview',
    'game_genres', 'game_developers', 'game_publishers', 'game_categories',
    'friends_association'
]