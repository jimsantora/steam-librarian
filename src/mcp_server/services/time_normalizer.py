"""Normalize time expressions to minutes using MCP sampling."""

import json
import logging
import re

from mcp import ClientSession, SamplingMessage

logger = logging.getLogger(__name__)


class TimeNormalizer:
    """Convert natural language time phrases to minute ranges."""

    def __init__(self, session: ClientSession | None = None):
        """Initialize with optional MCP client session."""
        self.session = session

    async def normalize_time(self, time_phrase: str) -> dict[str, int]:
        """Convert time phrases to minute ranges.

        Examples:
            "30 minutes" → {"min": 20, "max": 40}
            "quick session" → {"min": 0, "max": 30}
            "a few hours" → {"min": 120, "max": 240}
            "about an hour" → {"min": 45, "max": 75}
        """
        if not self.session:
            logger.warning("No MCP session available, falling back to pattern matching")
            return self._pattern_fallback(time_phrase)

        try:
            # Use sampling to interpret time expression
            messages = [
                SamplingMessage(
                    role="user",
                    content=f"""Convert this time expression to a range in minutes: "{time_phrase}"

Return a JSON object with "min" and "max" keys representing the likely range.
Be generous with ranges to account for variation.

Examples:
- "30 minutes" → {{"min": 20, "max": 40}}
- "quick game" → {{"min": 0, "max": 30}}
- "an hour" → {{"min": 45, "max": 75}}
- "couple hours" → {{"min": 90, "max": 180}}
- "all day" → {{"min": 300, "max": 999}}
- "15-20 minutes" → {{"min": 15, "max": 20}}

Return ONLY the JSON object.""",
                )
            ]

            result = await self.session.create_message(
                messages=messages,
                max_tokens=50,
                model_preferences={"hints": ["claude-3-haiku-20240307"]},
            )

            # Parse JSON response
            time_range = json.loads(result.content.text.strip())

            # Validate and ensure sensible values
            time_range["min"] = max(0, int(time_range.get("min", 0)))
            time_range["max"] = max(time_range["min"], int(time_range.get("max", 30)))

            logger.info(f"Normalized '{time_phrase}' to {time_range}")
            return time_range

        except Exception as e:
            logger.error(f"Sampling failed for time normalization: {e}")
            return self._pattern_fallback(time_phrase)

    def _pattern_fallback(self, time_phrase: str) -> dict[str, int]:
        """Fallback pattern matching when sampling isn't available."""
        phrase_lower = time_phrase.lower()

        # Quick sessions
        if any(word in phrase_lower for word in ["quick", "short", "brief"]):
            return {"min": 0, "max": 30}

        # Specific minute patterns
        minute_match = re.search(r"(\d+)(?:\s*-\s*(\d+))?\s*min", phrase_lower)
        if minute_match:
            min_val = int(minute_match.group(1))
            max_val = int(minute_match.group(2)) if minute_match.group(2) else min_val
            # Add some buffer
            return {"min": int(min_val * 0.8), "max": int(max_val * 1.2)}

        # Hour patterns
        hour_patterns = {
            r"half\s*(?:an\s*)?hour": {"min": 20, "max": 40},
            r"(?:about\s*)?an?\s*hour": {"min": 45, "max": 75},
            r"(?:a\s*)?couple\s*(?:of\s*)?hours?": {"min": 90, "max": 180},
            r"(?:a\s*)?few\s*hours?": {"min": 120, "max": 240},
            r"(\d+)\s*hours?": lambda m: {"min": int(m.group(1)) * 45, "max": int(m.group(1)) * 75},
        }

        for pattern, result in hour_patterns.items():
            match = re.search(pattern, phrase_lower)
            if match:
                if callable(result):
                    return result(match)
                return result

        # Time of day patterns
        if any(word in phrase_lower for word in ["evening", "afternoon", "night"]):
            return {"min": 120, "max": 300}

        if any(word in phrase_lower for word in ["all day", "whole day"]):
            return {"min": 300, "max": 999}

        # Long sessions
        if any(word in phrase_lower for word in ["long", "extended", "marathon"]):
            return {"min": 180, "max": 999}

        # Medium sessions
        if any(word in phrase_lower for word in ["medium", "moderate", "normal"]):
            return {"min": 60, "max": 120}

        # Default: assume medium session
        return {"min": 30, "max": 90}
