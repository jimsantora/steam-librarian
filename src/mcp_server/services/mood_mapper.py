"""Map sentiment expressions to supported moods using MCP sampling."""

import logging

from mcp import ClientSession, SamplingMessage

logger = logging.getLogger(__name__)


class MoodMapper:
    """Map any sentiment to our 5 supported moods."""

    SUPPORTED_MOODS = ["chill", "intense", "creative", "social", "nostalgic"]

    def __init__(self, session: ClientSession | None = None):
        """Initialize with optional MCP client session."""
        self.session = session

    async def map_to_mood(self, sentiment: str) -> str:
        """Map any sentiment expression to one of our supported moods.

        Examples:
            "relaxing" → "chill"
            "adrenaline rush" → "intense"
            "want to build stuff" → "creative"
            "play with friends" → "social"
            "old school games" → "nostalgic"
        """
        if not self.session:
            logger.warning("No MCP session available, falling back to keyword matching")
            return self._keyword_fallback(sentiment)

        try:
            # Use sampling to map sentiment
            messages = [
                SamplingMessage(
                    role="user",
                    content=f"""Map this sentiment to ONE of these moods: {', '.join(self.SUPPORTED_MOODS)}

Sentiment: "{sentiment}"

Mood definitions:
- chill: Relaxing, peaceful, low-stress, casual gameplay
- intense: Action-packed, challenging, adrenaline, competitive
- creative: Building, designing, expressing creativity, sandbox
- social: Multiplayer, co-op, party games, play with others
- nostalgic: Retro, classic, old-school, childhood memories

Examples:
- "want to relax" → chill
- "heart pumping action" → intense
- "build something" → creative
- "party with friends" → social
- "like the old days" → nostalgic

Return ONLY the mood word, nothing else.""",
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=10,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            mood = result.content.text.strip().lower()

            # Validate mood
            if mood in self.SUPPORTED_MOODS:
                logger.info(f"Mapped '{sentiment}' to mood: {mood}")
                return mood
            else:
                logger.warning(f"Invalid mood '{mood}' returned, using fallback")
                return self._keyword_fallback(sentiment)

        except Exception as e:
            logger.error(f"Sampling failed for mood mapping: {e}")
            return self._keyword_fallback(sentiment)

    def _keyword_fallback(self, sentiment: str) -> str:
        """Fallback keyword matching when sampling isn't available."""
        sentiment_lower = sentiment.lower()

        # Keywords for each mood, enhanced with Steam themes data from SteamDB.info
        mood_keywords = {
            "chill": [
                # Direct matches from Steam themes
                "relaxing",
                "atmospheric",
                "family friendly",
                "nature",
                "cozy",
                "peaceful",
                "zen",
                "casual",
                "easy",
                "unwind",
                "chill",
                "mellow",
                "laid back",
                "stress free",
                "comfortable",
                "soothing",
                "meditative",
                # Related themes
                "life sim",
                "farming",
                "cooking",
                "fishing",
                "cats",
                "dog",
            ],
            "intense": [
                # Direct matches from Steam themes
                "horror",
                "psychological horror",
                "survival horror",
                "thriller",
                "war",
                "military",
                "combat",
                "destruction",
                "competitive",
                # Action-oriented
                "intense",
                "action",
                "adrenaline",
                "exciting",
                "thrill",
                "challenge",
                "difficult",
                "hard",
                "fast",
                "rush",
                "pumping",
                "energetic",
                "hardcore",
                "bullet hell",
                "souls-like",
            ],
            "creative": [
                # Direct matches from Steam themes
                "building",
                "crafting",
                "management",
                "sandbox",
                "automation",
                "design",
                "level editor",
                "game development",
                "agriculture",
                # Creative expression
                "creative",
                "build",
                "create",
                "make",
                "craft",
                "construct",
                "imagine",
                "express",
                "artistic",
                "freedom",
                "open ended",
                "city builder",
                "base building",
            ],
            "social": [
                # Direct matches from Steam themes
                "multiplayer",
                "co-op",
                "team-based",
                "party",
                "online",
                "mmo",
                "moba",
                "battle royale",
                "esports",
                # Social aspects
                "social",
                "friends",
                "together",
                "group",
                "team",
                "community",
                "share",
                "collaborate",
                "dating sim",
                "romance",
            ],
            "nostalgic": [
                # Direct matches from Steam themes
                "retro",
                "old school",
                "1990s",
                "1980s",
                "pixel art",
                "arcade",
                "classic",
                "vintage",
                "8-bit",
                "16-bit",
                "traditional",
                # Historical themes
                "nostalgic",
                "old",
                "childhood",
                "memories",
                "past",
                "throwback",
                "timeless",
                "historical",
                "medieval",
                "world war",
                "alternate history",
            ],
        }

        # Score each mood based on keyword matches
        scores = {}
        for mood, keywords in mood_keywords.items():
            score = sum(1 for keyword in keywords if keyword in sentiment_lower)
            if score > 0:
                scores[mood] = score

        # Return mood with highest score, or default to chill
        if scores:
            best_mood = max(scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Keyword fallback mapped '{sentiment}' to mood: {best_mood}")
            return best_mood

        logger.info(f"No keyword matches for '{sentiment}', defaulting to 'chill'")
        return "chill"
