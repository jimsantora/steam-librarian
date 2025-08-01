"""Extract game features from natural language using MCP sampling."""

import json
import logging

from mcp import ClientSession, SamplingMessage
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract game features from text descriptions."""

    # Steam features based on actual usage data from SteamDB.info, organized by popularity
    GAME_FEATURES = [
        # Core gameplay features (most popular)
        "story-rich",  # 29,946 games
        "combat",  # 19,238 games
        "controller",  # 16,229 games
        "female-protagonist",  # 15,478 games
        "choices-matter",  # 14,443 games
        "pve",  # 13,675 games
        "pvp",  # 13,452 games
        "linear",  # 13,278 games
        "open-world",  # 13,158 games
        "multiple-endings",  # 12,704 games
        "physics",  # 11,700 games
        "character-customization",  # 11,519 games
        "crafting",  # 7,928 games
        "procedural-generation",  # 7,516 games
        "turn-based-combat",  # 7,411 games
        "turn-based-tactics",  # 7,328 games
        "resource-management",  # 7,240 games
        "tabletop",  # 6,922 games
        "hack-and-slash",  # 6,830 games
        "base-building",  # 5,973 games
        "score-attack",  # 5,384 games
        "text-based",  # 5,267 games
        "stealth",  # 4,824 games
        "narration",  # 4,660 games
        "conversation",  # 4,541 games
        "deckbuilding",  # 3,873 games
        "nonlinear",  # 3,836 games
        "tutorial",  # 3,664 games
        "perma-death",  # 3,485 games
        "team-based",  # 3,476 games
        "inventory-management",  # 3,253 games
        "artificial-intelligence",  # 2,973 games
        "level-editor",  # 2,477 games
        "grid-based-movement",  # 2,459 games
        "automation",  # 2,124 games
        "moddable",  # 2,005 games
        "class-based",  # 1,766 games
        "vehicular-combat",  # 1,697 games
        "gun-customization",  # 1,646 games
        "trading",  # 1,524 games
        "6dof",  # 1,455 games
        "bullet-time",  # 1,296 games
        "quick-time-events",  # 1,211 games
        "time-manipulation",  # 1,201 games
        "fmv",  # 1,099 games
        "dynamic-narration",  # 1,075 games
        "hex-grid",  # 999 games
        "naval-combat",  # 571 games
        "music-based-procedural-generation",  # 495 games
        "asymmetric-vr",  # 221 games
        # Additional common features
        "multiplayer",
        "single-player",
        "co-op",
        "online",
        "local-multiplayer",
        "achievements",
        "cloud-saves",
        "steam-workshop",
        "vr-support",
        "replay-value",
        "sandbox",
        "exploration",
        "puzzle-solving",
        "platforming",
        "racing",
        "flying",
        "space",
        "historical",
        "fantasy",
        "sci-fi",
        "realistic",
        "cartoonish",
        "pixel-art",
        "3d",
        "2d",
        "isometric",
        "first-person",
        "third-person",
        "top-down",
        "side-scrolling",
        "survival",
        "roguelike",
        "permadeath",
    ]

    def __init__(self, session: ClientSession | None = None):
        """Initialize with optional MCP client session."""
        self.session = session

    async def extract_features(self, description: str) -> list[str]:
        """Extract game features from a text description.

        Examples:
            "play with my friends online" → ["multiplayer", "online", "co-op"]
            "build bases and survive" → ["base-building", "survival", "crafting"]
            "story driven single player" → ["single-player", "story-rich"]
        """
        if not self.session:
            logger.warning("No MCP session available, falling back to keyword extraction")
            return self._keyword_fallback(description)

        try:
            # Use sampling to extract features
            messages = [
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Extract game features from this description: "{description}"

Available features: {', '.join(self.GAME_FEATURES[:30])} (and more)

Return a JSON array of relevant features. Focus on:
- Player count (single-player, multiplayer, co-op)
- Platform features (online, local, controller-support)
- Gameplay mechanics (crafting, building, combat, stealth)
- Game style (open-world, sandbox, story-rich)
- Visual style (pixel-art, 3d, realistic)

Examples:
- "play with friends" → ["multiplayer", "co-op", "online"]
- "epic single player story" → ["single-player", "story-rich"]
- "survival crafting game" → ["survival", "crafting", "base-building"]
- "retro platformer" → ["platforming", "pixel-art", "2d", "side-scrolling"]

Return ONLY the JSON array.""",
                    ),
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=150,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            # Parse JSON response
            features = json.loads(result.content.text.strip())

            # Validate features against known list (be lenient)
            valid_features = []
            for feature in features:
                normalized = feature.lower().replace(" ", "-").replace("_", "-")
                if normalized in self.GAME_FEATURES:
                    valid_features.append(normalized)
                elif any(normalized in gf for gf in self.GAME_FEATURES):
                    # Partial match
                    matching = [gf for gf in self.GAME_FEATURES if normalized in gf]
                    valid_features.extend(matching[:1])  # Take first match

            # Remove duplicates
            valid_features = list(dict.fromkeys(valid_features))

            logger.info(f"Extracted features from '{description}': {valid_features}")
            return valid_features

        except Exception as e:
            logger.error(f"Sampling failed for feature extraction: {e}")
            return self._keyword_fallback(description)

    def _keyword_fallback(self, description: str) -> list[str]:
        """Fallback keyword extraction when sampling isn't available."""
        desc_lower = description.lower()
        extracted = []

        # Direct feature matching
        for feature in self.GAME_FEATURES:
            # Convert feature to searchable terms
            search_terms = [
                feature,
                feature.replace("-", " "),
                feature.replace("-", ""),
            ]

            if any(term in desc_lower for term in search_terms):
                extracted.append(feature)

        # Special keyword mappings
        keyword_features = {
            "friends": ["multiplayer", "co-op", "online"],
            "alone": ["single-player"],
            "solo": ["single-player"],
            "together": ["multiplayer", "co-op"],
            "online": ["online", "multiplayer"],
            "local": ["local-multiplayer"],
            "build": ["building", "crafting", "sandbox"],
            "survive": ["survival", "crafting"],
            "story": ["story-rich", "single-player"],
            "explore": ["exploration", "open-world"],
            "fight": ["combat", "pvp"],
            "sneak": ["stealth"],
            "puzzle": ["puzzle-solving"],
            "jump": ["platforming"],
            "race": ["racing"],
            "fly": ["flying"],
            "space": ["space", "sci-fi"],
            "fantasy": ["fantasy"],
            "real": ["realistic"],
            "cartoon": ["cartoonish"],
            "pixel": ["pixel-art", "2d"],
            "retro": ["pixel-art", "2d"],
            "fps": ["first-person", "shooter"],
            "tps": ["third-person"],
            "vr": ["vr-support"],
            "mod": ["moddable", "steam-workshop"],
        }

        for keyword, features in keyword_features.items():
            if keyword in desc_lower:
                extracted.extend(features)

        # Remove duplicates and return
        return list(dict.fromkeys(extracted)) or ["single-player"]  # Default
