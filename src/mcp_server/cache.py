"""Intelligent caching system for Steam Librarian MCP Server"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)


class SmartCache:
    """Multi-tier caching with TTL and invalidation support"""

    def __init__(self, cache_dir: str = "./cache"):
        self.memory_cache = {}  # Hot cache in memory
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._cleanup_task = None

    async def _ensure_cleanup_task(self):
        """Ensure cleanup task is running"""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            except RuntimeError:
                # No event loop running, cleanup will happen on demand
                pass

    async def get(self, key: str) -> Any | None:
        """Get value from cache if it exists and hasn't expired"""
        if not settings.enable_cache:
            return None

        # Check memory cache first
        if key in self.memory_cache:
            value, timestamp = self.memory_cache[key]
            if time.time() - timestamp < settings.cache_ttl:
                logger.debug(f"Cache hit (memory): {key}")
                return value

        # Check disk cache
        if settings.cache_backend in ["disk", "hybrid"]:
            disk_value = await self._get_from_disk(key)
            if disk_value and not self._is_expired(disk_value, settings.cache_ttl):
                # Promote to memory cache
                self.memory_cache[key] = (disk_value["value"], time.time())
                logger.debug(f"Cache hit (disk): {key}")
                return disk_value["value"]

        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with optional TTL"""
        if not settings.enable_cache:
            return

        ttl = ttl or settings.cache_ttl
        await self._cache_value(key, value, ttl)

    async def get_or_compute(self, key: str, compute_func: Callable, ttl: int = None) -> Any:
        """Get value from cache or compute it"""
        if not settings.enable_cache:
            return await compute_func()

        # Ensure cleanup task is running
        await self._ensure_cleanup_task()

        ttl = ttl or settings.cache_ttl

        # Check memory cache first
        if key in self.memory_cache:
            value, timestamp = self.memory_cache[key]
            if time.time() - timestamp < ttl:
                logger.debug(f"Cache hit (memory): {key}")
                return value

        # Check disk cache
        if settings.cache_backend in ["disk", "hybrid"]:
            disk_value = await self._get_from_disk(key)
            if disk_value and not self._is_expired(disk_value, ttl):
                # Promote to memory cache
                self.memory_cache[key] = (disk_value["value"], time.time())
                logger.debug(f"Cache hit (disk): {key}")
                return disk_value["value"]

        # Cache miss - compute value
        logger.debug(f"Cache miss: {key}")
        value = await compute_func()

        # Store in cache
        await self._cache_value(key, value, ttl)

        return value

    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        # Invalidate memory cache
        keys_to_remove = [k for k in self.memory_cache if pattern in k]
        for key in keys_to_remove:
            del self.memory_cache[key]
            logger.debug(f"Invalidated memory cache: {key}")

        # Invalidate disk cache
        if settings.cache_backend in ["disk", "hybrid"]:
            for cache_file in self.cache_dir.glob("*.json"):
                if pattern in cache_file.stem:
                    cache_file.unlink()
                    logger.debug(f"Invalidated disk cache: {cache_file.stem}")

    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user"""
        await self.invalidate(user_id)

    async def _cache_value(self, key: str, value: Any, ttl: int):
        """Store value in cache"""
        # Always store in memory
        self.memory_cache[key] = (value, time.time())

        # Store on disk if configured
        if settings.cache_backend in ["disk", "hybrid"]:
            await self._save_to_disk(key, value, ttl)

    async def _get_from_disk(self, key: str) -> dict | None:
        """Load value from disk cache"""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache file {cache_file}: {e}")
            return None

    async def _save_to_disk(self, key: str, value: Any, ttl: int):
        """Save value to disk cache"""
        cache_file = self.cache_dir / f"{key}.json"
        cache_data = {"value": value, "timestamp": time.time(), "ttl": ttl, "expires": datetime.now().isoformat()}

        try:
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")

    def _is_expired(self, cache_data: dict, ttl: int) -> bool:
        """Check if cached data is expired"""
        timestamp = cache_data.get("timestamp", 0)
        return time.time() - timestamp > ttl

    async def _periodic_cleanup(self):
        """Periodically clean up expired cache entries"""
        while True:
            try:
                # Clean memory cache
                current_time = time.time()
                expired_keys = []
                for key, (_value, timestamp) in self.memory_cache.items():
                    if current_time - timestamp > settings.cache_ttl:
                        expired_keys.append(key)

                for key in expired_keys:
                    del self.memory_cache[key]

                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired memory cache entries")

                # Clean disk cache
                if settings.cache_backend in ["disk", "hybrid"]:
                    cleaned = 0
                    for cache_file in self.cache_dir.glob("*.json"):
                        try:
                            with open(cache_file) as f:
                                data = json.load(f)
                            if self._is_expired(data, data.get("ttl", settings.cache_ttl)):
                                cache_file.unlink()
                                cleaned += 1
                        except Exception:
                            # Remove corrupted cache files
                            cache_file.unlink()
                            cleaned += 1

                    if cleaned:
                        logger.info(f"Cleaned up {cleaned} expired disk cache entries")

            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

            # Run cleanup every hour
            await asyncio.sleep(3600)


# Global cache instance
cache = SmartCache()


# Cache key generators
def user_cache_key(prefix: str, user_id: str) -> str:
    """Generate cache key for user-specific data"""
    return f"{prefix}_{user_id}"


def game_cache_key(prefix: str, app_id: str) -> str:
    """Generate cache key for game-specific data"""
    return f"{prefix}_game_{app_id}"


def search_cache_key(query: str, user_id: str | None = None) -> str:
    """Generate cache key for search results"""
    key = f"search_{hash(query)}"
    if user_id:
        key += f"_{user_id}"
    return key
