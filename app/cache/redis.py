import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis caching abstraction with graceful failure handling."""

    def __init__(self, client: Redis):
        self.client = client

    async def get_json(self, key: str) -> Any | None:
        try:
            value = await self.client.get(key)

            if value is None:
                return None

            return json.loads(value)

        except (RedisError, ValueError, TypeError):
            logger.warning("Redis cache read failed: %s", key)
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int,
    ) -> bool:
        try:
            serialized = json.dumps(value)

            await self.client.set(
                key,
                serialized,
                ex=ttl,
            )

            return True

        except (RedisError, ValueError, TypeError):
            logger.warning("Redis cache write failed: %s", key)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True

        except RedisError:
            logger.warning("Redis cache deletion failed: %s", key)
            return False

    async def invalidate_market_data(
        self,
        exchange: str,
        symbol: str,
    ) -> None:
        """Invalidate latest price and related history entries."""

        exchange = exchange.lower()
        symbol = symbol.upper()

        latest_key = (
            f"market:v1:latest:{exchange}:{symbol}"
        )

        history_pattern = (
            f"market:v1:history:{exchange}:{symbol}:*"
        )

        await self.delete(latest_key)

        try:
            keys = []

            async for key in self.client.scan_iter(
                match=history_pattern,
                count=100,
            ):
                keys.append(key)

            if keys:
                await self.client.delete(*keys)

        except RedisError:
            logger.warning(
                "Market data cache invalidation failed: %s %s",
                exchange,
                symbol,
            )

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())

        except RedisError:
            return False