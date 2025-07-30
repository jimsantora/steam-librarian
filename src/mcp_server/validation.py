"""Input validation for Steam Librarian MCP Server"""

import re

from pydantic import BaseModel, Field, field_validator


class SteamIDValidator:
    """Validate and normalize Steam ID formats"""

    @staticmethod
    def validate(steam_id: str | None) -> str | None:
        """Validate Steam ID format"""
        if not steam_id:
            return None

        steam_id = steam_id.strip()

        # Check if it's a valid Steam64 ID (17 digits)
        if re.match(r"^\d{17}$", steam_id):
            return steam_id

        # Check if it's a valid Steam3 ID [U:1:XXXXXXXX]
        if re.match(r"^\[U:1:\d+\]$", steam_id):
            # Convert to Steam64 format
            match = re.search(r"\[U:1:(\d+)\]", steam_id)
            if match:
                account_id = int(match.group(1))
                return str(76561197960265728 + account_id)

        raise ValueError(f"Invalid Steam ID format: {steam_id}")


class QuerySanitizer:
    """Sanitize and validate search queries"""

    @staticmethod
    def sanitize(query: str) -> str:
        """Sanitize search queries to prevent injection attacks"""
        if not query:
            raise ValueError("Query cannot be empty")

        # Remove SQL injection attempts
        dangerous_patterns = [r";\s*DROP", r";\s*DELETE", r"UNION\s+SELECT", r"OR\s+1=1", r"--\s*$", r"/\*.*\*/"]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError("Invalid query detected")

        # Limit length
        if len(query) > 200:
            query = query[:200]

        # Clean up whitespace
        query = " ".join(query.split())

        return query


# Pydantic models for input validation
class SearchGamesInput(BaseModel):
    """Validate search_games tool input"""

    query: str = Field(..., min_length=1, max_length=200)
    user_steam_id: str | None = None

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v):
        return QuerySanitizer.sanitize(v)

    @field_validator("user_steam_id")
    @classmethod
    def validate_steam_id(cls, v):
        if v:
            return SteamIDValidator.validate(v)
        return v


class FilterGamesInput(BaseModel):
    """Validate filter_games tool input"""

    user_steam_id: str | None = None
    playtime_min: float | None = Field(None, ge=0)
    playtime_max: float | None = Field(None, ge=0)
    review_summary: list[str] | None = None
    maturity_rating: str | None = None
    preset: str | None = None
    categories: list[str] | None = None
    sort_by: str | None = None

    @field_validator("user_steam_id")
    @classmethod
    def validate_steam_id(cls, v):
        if v:
            return SteamIDValidator.validate(v)
        return v

    @field_validator("playtime_min", "playtime_max")
    @classmethod
    def validate_playtime(cls, v):
        if v is not None and v < 0:
            raise ValueError("Playtime cannot be negative")
        return v

    @field_validator("review_summary")
    @classmethod
    def validate_review_summary(cls, v):
        if v:
            valid_summaries = ["Overwhelmingly Positive", "Very Positive", "Positive", "Mostly Positive", "Mixed", "Mostly Negative", "Negative", "Very Negative", "Overwhelmingly Negative"]
            for summary in v:
                if summary not in valid_summaries:
                    raise ValueError(f"Invalid review summary: {summary}")
        return v

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, v):
        if v:
            valid_presets = ["comfort_food", "hidden_gems", "quick_session", "deep_dive"]
            if v not in valid_presets:
                raise ValueError(f"Invalid preset: {v}")
        return v


class RecommendationsInput(BaseModel):
    """Validate get_recommendations tool input"""

    user_steam_id: str
    context: dict | None = None

    @field_validator("user_steam_id")
    @classmethod
    def validate_steam_id(cls, v):
        return SteamIDValidator.validate(v)

    @field_validator("context")
    @classmethod
    def validate_context(cls, v):
        if v:
            # Validate known context keys
            valid_keys = ["mood", "time_available", "exclude_recent", "with_friends"]
            for key in v:
                if key not in valid_keys:
                    raise ValueError(f"Unknown context key: {key}")
        return v


class FriendsDataInput(BaseModel):
    """Validate get_friends_data tool input"""

    data_type: str
    user_steam_id: str | None = None
    friend_steam_id: str | None = None
    game_identifier: str | None = None

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v):
        valid_types = ["common_games", "friend_activity", "multiplayer_compatible", "compatibility_score"]
        if v not in valid_types:
            raise ValueError(f"Invalid data type: {v}")
        return v

    @field_validator("user_steam_id", "friend_steam_id")
    @classmethod
    def validate_steam_id(cls, v):
        if v:
            return SteamIDValidator.validate(v)
        return v


class LibraryStatsInput(BaseModel):
    """Validate get_library_stats tool input"""

    user_steam_id: str
    time_period: str | None = "all_time"
    include_insights: bool = True

    @field_validator("user_steam_id")
    @classmethod
    def validate_steam_id(cls, v):
        return SteamIDValidator.validate(v)

    @field_validator("time_period")
    @classmethod
    def validate_time_period(cls, v):
        valid_periods = ["all_time", "last_year", "last_6_months", "last_month", "last_week"]
        if v not in valid_periods:
            raise ValueError(f"Invalid time period: {v}")
        return v
