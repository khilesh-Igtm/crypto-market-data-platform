import asyncio
import logging
import signal
from collections.abc import Callable

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import RedisCache
from app.core.config import get_settings
from app.db.session import AsyncSessionFactory, engine
from app.exchanges.binance.client import BinanceClient
from app.exchanges.binance.normalizer import normalize_ticker_price
from app.market_data.service import persist_market_price

logger = logging.getLogger(__name__)


def parse_symbols(value: str) -> list[str]:
    """
    Parse comma-separated symbols and remove duplicates.
    """

    symbols = [
        symbol.strip().upper()
        for symbol in value.split(",")
        if symbol.strip()
    ]

    return list(dict.fromkeys(symbols))


class MarketDataIngestionWorker:
    """
    Continuously fetches market prices from Binance
    and persists them in PostgreSQL.
    """

    def __init__(
        self,
        client: BinanceClient | None = None,
        session_factory: Callable[[], AsyncSession] | None = None,
        cache: RedisCache | None = None,
        symbols: list[str] | None = None,
        poll_interval: float | None = None,
        stop_event: asyncio.Event | None = None,
    ):
        settings = get_settings()

        self.client = client or BinanceClient()
        self.session_factory = session_factory or AsyncSessionFactory
        self.cache = cache

        self.symbols = symbols or parse_symbols(
            settings.ingestion_symbols
        )

        self.poll_interval = (
            poll_interval
            if poll_interval is not None
            else settings.ingestion_poll_interval_seconds
        )

        self.stop_event = stop_event or asyncio.Event()

        if not self.symbols:
            raise ValueError("At least one ingestion symbol is required.")

        if self.poll_interval <= 0:
            raise ValueError("Poll interval must be greater than zero.")

    async def ingest_symbol(self, symbol: str) -> bool:
        """
        Fetch, normalize and persist one symbol.
        """

        try:
            response = await self.client.get_ticker_price(symbol)

            market_price = normalize_ticker_price(response)

            async with self.session_factory() as session:
                await persist_market_price(
                    session=session,
                    market_price=market_price,
                    cache=self.cache,
                )

            logger.info(
                "Market price persisted: %s = %s",
                market_price.symbol,
                market_price.price,
            )

            return True

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Failed to ingest market data for %s",
                symbol,
            )
            return False

    async def ingest_once(self) -> int:
        """
        Execute one ingestion cycle for all configured symbols.

        Returns the number of successfully ingested symbols.
        """

        results = await asyncio.gather(
            *(
                self.ingest_symbol(symbol)
                for symbol in self.symbols
            )
        )

        successful = sum(results)

        logger.info(
            "Ingestion cycle completed: %s/%s symbols successful",
            successful,
            len(self.symbols),
        )

        return successful

    async def run(self) -> None:
        """
        Run ingestion continuously until shutdown is requested.
        """

        logger.info(
            "Starting market data worker. Symbols: %s | Interval: %s seconds",
            ", ".join(self.symbols),
            self.poll_interval,
        )

        while not self.stop_event.is_set():
            cycle_started = asyncio.get_running_loop().time()

            await self.ingest_once()

            elapsed = (
                asyncio.get_running_loop().time() - cycle_started
            )

            # Maintain the configured polling interval.
            wait_time = max(
                0,
                self.poll_interval - elapsed,
            )

            if wait_time > 0:
                try:
                    await asyncio.wait_for(
                        self.stop_event.wait(),
                        timeout=wait_time,
                    )
                except TimeoutError:
                    pass

        logger.info("Market data worker stopped gracefully.")


async def main() -> None:
    """
    Initialize resources and run the independent worker.
    """

    settings = get_settings()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # Handle Ctrl+C and termination signals.
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                sig,
                stop_event.set,
            )
        except (NotImplementedError, RuntimeError, ValueError):
            signal.signal(
                sig,
                lambda *_: loop.call_soon_threadsafe(
                    stop_event.set
                ),
            )

    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )

    cache = RedisCache(redis_client)

    worker = MarketDataIngestionWorker(
        cache=cache,
        stop_event=stop_event,
    )

    try:
        await worker.run()

    finally:
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    asyncio.run(main())