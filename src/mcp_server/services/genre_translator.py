"""Translate natural language phrases to Steam genres using MCP sampling."""

import json
import logging

from mcp import ClientSession, SamplingMessage
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class GenreTranslator:
    """Translate natural language to Steam genres using MCP sampling."""

    # Top Steam genres based on actual usage data from SteamDB.info, ordered by popularity
    STEAM_GENRES = [
        # Core genres (most popular)
        "Puzzle",
        "Action-Adventure",
        "Arcade",
        "Shooter",
        "Platformer",
        "Visual Novel",
        "Roguelike",
        "Sandbox",
        "Action RPG",
        "Point & Click",
        "Action Roguelike",
        "Interactive Fiction",
        "Turn-Based Strategy",
        "Tabletop",
        "Dating Sim",
        "Education",
        "Walking Simulator",
        "JRPG",
        "Party-Based RPG",
        "Card Game",
        "Life Sim",
        "Design & Illustration",
        "Strategy RPG",
        "Utilities",
        "Board Game",
        "RTS",
        "Tower Defense",
        "City Builder",
        "Web Publishing",
        "Beat 'em up",
        "Automobile Sim",
        "2D Fighter",
        "Rhythm",
        "Farming Sim",
        "3D Fighter",
        "Word Game",
        "eSports",
        "Colony Sim",
        "Auto Battler",
        "Grand Strategy",
        "Space Sim",
        "Animation & Modeling",
        "Battle Royale",
        "MMORPG",
        "Audio Production",
        "God Game",
        "Video Production",
        "4X",
        "MOBA",
        "Trivia",
        "Photo Editing",
        # Important sub-genres
        "Exploration",
        "2D Platformer",
        "FPS",
        "Roguelite",
        "Immersive Sim",
        "3D Platformer",
        "Choose Your Own Adventure",
        "Shoot 'Em Up",
        "Side Scroller",
        "Puzzle Platformer",
        "Turn-Based Tactics",
        "Hidden Object",
        "Hack and Slash",
        "Bullet Hell",
        "Dungeon Crawler",
        "Clicker",
        "Top-Down Shooter",
        "Third-Person Shooter",
        "Time Management",
        "Precision Platformer",
        "Collectathon",
        "Real Time Tactics",
        "Idler",
        "Arena Shooter",
        "Tactical RPG",
        "Card Battler",
        "Wargame",
        "Metroidvania",
        "Souls-like",
        "Runner",
        "Flight",
        "Creature Collector",
        "CRPG",
        "Twin Stick Shooter",
        "Mystery Dungeon",
        "Match 3",
        "Hero Shooter",
        "Looter Shooter",
        "Spectacle fighter",
        "Solitaire",
        "Combat Racing",
        "Action RTS",
        "Sokoban",
        "Trading Card Game",
        "Boomer Shooter",
        "Political Sim",
        "Typing",
        "On-Rails Shooter",
        "Traditional Roguelike",
        "Spelling",
        "Outbreak Sim",
        "Roguevania",
        "Medical Sim",
    ]

    def __init__(self, session: ClientSession | None = None):
        """Initialize with optional MCP client session."""
        self.session = session

    async def translate_to_genres(self, phrase: str) -> list[str]:
        """Translate a natural language phrase to Steam genres.

        Examples:
            "brain teasers" → ["Puzzle", "Strategy"]
            "scary games" → ["Horror", "Survival"]
            "games to play with friends" → ["Multiplayer", "Co-op"]
        """
        if not self.session:
            logger.warning("No MCP session available, falling back to keyword matching")
            return self._keyword_fallback(phrase)

        try:
            # Use sampling to get genre mapping
            messages = [
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Given this phrase: "{phrase}"

What Steam genres best match? Choose from: {', '.join(self.STEAM_GENRES)}

Return a JSON array of matching genres. Be generous and include related genres.

Examples:
- "brain teasers" → ["Puzzle", "Strategy", "Mystery"]
- "scary games" → ["Horror", "Survival", "Mystery"]
- "quick fun" → ["Casual", "Puzzle", "Indie"]
- "games like portal" → ["Puzzle", "Platformer", "Indie"]

Return ONLY the JSON array, no explanation.""",
                    ),
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=100,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            # Parse JSON response
            genres = json.loads(result.content.text.strip())
            # Validate genres against known list
            valid_genres = [g for g in genres if g in self.STEAM_GENRES]

            logger.info(f"Translated '{phrase}' to genres: {valid_genres}")
            return valid_genres

        except Exception as e:
            logger.error(f"Sampling failed for genre translation: {e}")
            return self._keyword_fallback(phrase)

    async def find_similar_genres(self, genre: str) -> list[str]:
        """Find genres similar to the given genre.

        Example: "Puzzle" → ["Strategy", "Casual", "Mystery"]
        """
        if not self.session:
            return self._similarity_fallback(genre)

        try:
            messages = [
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Given the Steam genre: "{genre}"

What other genres are most similar or often enjoyed by the same players?
Choose from: {', '.join(self.STEAM_GENRES)}

Return a JSON array of 3-5 similar genres. Don't include the original genre.

Examples:
- "Puzzle" → ["Strategy", "Casual", "Mystery", "Indie"]
- "Action" → ["Adventure", "Shooter", "Platformer", "Fighting"]
- "RPG" → ["Adventure", "Strategy", "Open World", "Fantasy"]

Return ONLY the JSON array.""",
                    ),
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=100,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            similar = json.loads(result.content.text.strip())
            valid_similar = [g for g in similar if g in self.STEAM_GENRES and g != genre]

            logger.info(f"Found similar genres for '{genre}': {valid_similar}")
            return valid_similar[:5]  # Limit to 5

        except Exception as e:
            logger.error(f"Sampling failed for similar genres: {e}")
            return self._similarity_fallback(genre)

    def _keyword_fallback(self, phrase: str) -> list[str]:
        """Fallback keyword matching when sampling isn't available."""
        phrase_lower = phrase.lower()
        matches = []

        # Keyword mappings
        keyword_map = {
            "brain": ["Puzzle", "Strategy"],
            "puzzle": ["Puzzle", "Mystery"],
            "scary": ["Horror", "Survival"],
            "horror": ["Horror", "Survival"],
            "multiplayer": ["Massively Multiplayer"],
            "friends": ["Massively Multiplayer"],
            "quick": ["Casual", "Indie"],
            "relax": ["Casual", "Simulation"],
            "build": ["Building", "Sandbox", "Simulation"],
            "fight": ["Fighting", "Action"],
            "shoot": ["Shooter", "Action"],
            "race": ["Racing", "Sports"],
            "sport": ["Sports", "Racing"],
            "story": ["Adventure", "RPG", "Visual Novel"],
            "explore": ["Open World", "Adventure", "Sandbox"],
            "survive": ["Survival", "Horror"],
            "strategy": ["Strategy", "Simulation"],
            "card": ["Card Game", "Strategy"],
        }

        for keyword, genres in keyword_map.items():
            if keyword in phrase_lower:
                matches.extend(genres)

        # Remove duplicates and return
        return list(dict.fromkeys(matches)) or ["Indie"]  # Default to Indie if no matches

    def _similarity_fallback(self, genre: str) -> list[str]:
        """Fallback for finding similar genres based on actual Steam usage patterns."""
        similarity_map = {
            "Puzzle": ["Puzzle Platformer", "Hidden Object", "Point & Click", "Logic"],
            "Action-Adventure": ["Adventure", "Action RPG", "Open World", "Exploration"],
            "Shooter": ["FPS", "Third-Person Shooter", "Top-Down Shooter", "Arena Shooter"],
            "Platformer": ["2D Platformer", "3D Platformer", "Precision Platformer", "Metroidvania"],
            "Roguelike": ["Roguelite", "Action Roguelike", "Traditional Roguelike", "Dungeon Crawler"],
            "Action RPG": ["RPG", "Hack and Slash", "JRPG", "Party-Based RPG"],
            "Visual Novel": ["Interactive Fiction", "Choose Your Own Adventure", "Dating Sim"],
            "Strategy": ["Turn-Based Strategy", "RTS", "Turn-Based Tactics", "Grand Strategy"],
            "Card Game": ["Card Battler", "Deckbuilding", "Trading Card Game", "Solitaire"],
            "Sandbox": ["Building", "Open World", "Crafting", "City Builder"],
            "Horror": ["Survival Horror", "Psychological Horror", "Mystery"],
            "RPG": ["Action RPG", "JRPG", "Strategy RPG", "Party-Based RPG"],
            "Simulation": ["Life Sim", "Farming Sim", "City Builder", "Space Sim"],
            "Fighting": ["2D Fighter", "3D Fighter", "Beat 'em up", "Spectacle fighter"],
            "Racing": ["Combat Racing", "Automobile Sim", "Arcade"],
            "FPS": ["Shooter", "Hero Shooter", "Boomer Shooter", "Arena Shooter"],
            "Arcade": ["Action", "Shoot 'Em Up", "Bullet Hell", "Runner"],
            "Indie": ["Puzzle", "Platformer", "Action-Adventure", "Visual Novel"],
            "Turn-Based Strategy": ["Strategy", "Turn-Based Tactics", "4X", "Wargame"],
            "Metroidvania": ["Platformer", "Action-Adventure", "Exploration"],
            "Souls-like": ["Action RPG", "Hack and Slash", "Dungeon Crawler"],
            "Battle Royale": ["Shooter", "Survival", "PvP"],
            "MOBA": ["Strategy", "Team-Based", "PvP"],
            "Tower Defense": ["Strategy", "RTS", "Real Time Tactics"],
            "City Builder": ["Simulation", "Management", "Strategy"],
            "Bullet Hell": ["Shoot 'Em Up", "Arcade", "Shooter"],
            "Clicker": ["Idler", "Casual", "Management"],
        }

        return similarity_map.get(genre, ["Puzzle", "Action-Adventure"])[:4]
