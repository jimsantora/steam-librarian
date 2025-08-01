"""Extract game references from queries using MCP sampling."""

import logging
import re

from mcp import ClientSession, SamplingMessage
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class SimilarityFinder:
    """Extract game references from natural language queries."""

    def __init__(self, session: ClientSession | None = None):
        """Initialize with optional MCP client session."""
        self.session = session

    async def extract_game_name(self, query: str) -> str | None:
        """Extract a game name from a similarity query.

        Examples:
            "games like Portal" → "Portal"
            "something similar to Hades" → "Hades"
            "Portal-style games" → "Portal"
            "puzzle games" → None
            "games" → None
        """
        if not self.session:
            logger.warning("No MCP session available, falling back to pattern matching")
            return self._pattern_fallback(query)

        try:
            # Use sampling to extract game reference
            messages = [
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Extract the game name being referenced in this query: "{query}"

If the query mentions a specific game for comparison, return just the game name.
If no specific game is mentioned, return null.

Examples:
- "games like Portal" → "Portal"
- "something similar to Hades" → "Hades"
- "Portal-style puzzle games" → "Portal"
- "games similar to The Witcher 3" → "The Witcher 3"
- "Half-Life inspired games" → "Half-Life"
- "puzzle games" → null
- "action games" → null
- "something fun" → null

Return ONLY the game name or null, nothing else.""",
                    ),
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=50,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            response = result.content.text.strip()

            # Handle response
            if response.lower() in ["null", "none", ""]:
                logger.info(f"No game reference found in: '{query}'")
                return None

            # Clean up game name (remove quotes if present)
            game_name = response.strip("\"'")

            logger.info(f"Extracted game reference '{game_name}' from: '{query}'")
            return game_name

        except Exception as e:
            logger.error(f"Sampling failed for game extraction: {e}")
            return self._pattern_fallback(query)

    def _pattern_fallback(self, query: str) -> str | None:
        """Fallback pattern matching when sampling isn't available."""
        query_lower = query.lower()

        # Patterns that indicate game similarity queries
        patterns = [
            # "games like X"
            r"games?\s+(?:like|similar\s+to)\s+([^,\.\?!]+)",
            # "similar to X"
            r"similar\s+to\s+([^,\.\?!]+?)(?:\s+games?)?$",
            # "X-style", "X-like", "X inspired"
            r"([^,\.\?!\s]+?)(?:-style|-like|-inspired)\s+",
            # "something like X"
            r"something\s+like\s+([^,\.\?!]+)",
            # "in the style of X"
            r"in\s+the\s+style\s+of\s+([^,\.\?!]+)",
            # "reminds me of X"
            r"reminds?\s+(?:me\s+)?of\s+([^,\.\?!]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                game_name = match.group(1).strip()

                # Clean up common suffixes
                game_name = re.sub(r"\s+(game|games|series|franchise)s?$", "", game_name)

                # Don't return generic terms
                generic_terms = ["something", "anything", "a game", "games", "stuff"]
                if game_name in generic_terms:
                    continue

                # Capitalize properly (simple title case)
                game_name = " ".join(word.capitalize() for word in game_name.split())

                logger.info(f"Pattern extracted game reference '{game_name}' from: '{query}'")
                return game_name

        logger.info(f"No game reference found via patterns in: '{query}'")
        return None
