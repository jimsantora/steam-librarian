"""Steam username to Steam ID resolution service"""

import logging
import os

from aiohttp import ClientSession

logger = logging.getLogger(__name__)


class UsernameResolver:
    """Resolve Steam usernames to Steam IDs using Steam Web API"""

    def __init__(self, session: ClientSession | None = None):
        self.session = session
        self.api_key = os.getenv("STEAM_API_KEY")
        self.base_url = "https://api.steampowered.com"

    async def resolve_username(self, username: str) -> str | None:
        """
        Resolve a Steam username/vanity URL to Steam ID.

        Args:
            username: Steam username or vanity URL name

        Returns:
            Steam ID as string if found, None otherwise
        """

        # Check if it's already a Steam ID (17 digits)
        if username.isdigit() and len(username) == 17:
            return username

        # If no API key, can't resolve usernames
        if not self.api_key:
            logger.warning("No STEAM_API_KEY found, cannot resolve username to Steam ID")
            return None

        try:
            # Use Steam Web API to resolve vanity URL
            url = f"{self.base_url}/ISteamUser/ResolveVanityURL/v0001/"
            params = {"key": self.api_key, "vanityurl": username, "url_type": 1}  # Individual profile

            if self.session:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_resolve_response(data, username)
                    else:
                        logger.warning(f"Steam API returned status {response.status} for username: {username}")
                        return None
            else:
                # Fallback without session (shouldn't happen in normal use)
                async with ClientSession() as temp_session:
                    async with temp_session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_resolve_response(data, username)
                        else:
                            logger.warning(f"Steam API returned status {response.status} for username: {username}")
                            return None

        except Exception as e:
            logger.error(f"Error resolving username '{username}': {e}")
            return None

    def _parse_resolve_response(self, data: dict, username: str) -> str | None:
        """Parse Steam API resolve response"""

        try:
            response = data.get("response", {})
            success = response.get("success", 0)

            if success == 1:
                steam_id = response.get("steamid")
                if steam_id:
                    logger.info(f"Resolved username '{username}' to Steam ID: {steam_id}")
                    return steam_id
            elif success == 42:
                logger.info(f"Username '{username}' not found on Steam")
            else:
                logger.warning(f"Steam API returned success={success} for username: {username}")

            return None

        except Exception as e:
            logger.error(f"Error parsing Steam API response for username '{username}': {e}")
            return None

    async def validate_steam_id(self, steam_id: str) -> bool:
        """
        Validate that a Steam ID exists and is accessible.

        Args:
            steam_id: Steam ID to validate

        Returns:
            True if valid and accessible, False otherwise
        """

        if not self.api_key:
            logger.warning("No STEAM_API_KEY found, cannot validate Steam ID")
            return False

        try:
            # Use GetPlayerSummaries to check if Steam ID exists
            url = f"{self.base_url}/ISteamUser/GetPlayerSummaries/v0002/"
            params = {"key": self.api_key, "steamids": steam_id}

            if self.session:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_validation_response(data, steam_id)
                    else:
                        logger.warning(f"Steam API returned status {response.status} for Steam ID: {steam_id}")
                        return False
            else:
                async with ClientSession() as temp_session:
                    async with temp_session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self._parse_validation_response(data, steam_id)
                        else:
                            logger.warning(f"Steam API returned status {response.status} for Steam ID: {steam_id}")
                            return False

        except Exception as e:
            logger.error(f"Error validating Steam ID '{steam_id}': {e}")
            return False

    def _parse_validation_response(self, data: dict, steam_id: str) -> bool:
        """Parse Steam API validation response"""

        try:
            response = data.get("response", {})
            players = response.get("players", [])

            if players and len(players) > 0:
                player = players[0]
                # Check if profile is visible (has persona name)
                if player.get("personaname"):
                    logger.info(f"Steam ID {steam_id} is valid and accessible")
                    return True
                else:
                    logger.info(f"Steam ID {steam_id} exists but profile may be private")
                    return True  # Still valid, just private
            else:
                logger.info(f"Steam ID {steam_id} not found or not accessible")
                return False

        except Exception as e:
            logger.error(f"Error parsing Steam API validation response for Steam ID '{steam_id}': {e}")
            return False
