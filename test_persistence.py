import asyncio

from app.db.repositories.market_data import MarketDataRepository
from app.db.session import AsyncSessionFactory, engine
from app.exchanges.binance.client import BinanceClient
from app.exchanges.binance.normalizer import normalize_ticker_price
from app.market_data.service import persist_market_price


async def main() -> None:
    try:
        # 1. Fetch live price from Binance
        client = BinanceClient()
        response = await client.get_ticker_price("BTCUSDT")

        print("Binance response:", response)

        # 2. Normalize exchange response
        market_price = normalize_ticker_price(response)

        print("Normalized price:", market_price)

        # 3. Persist normalized data in PostgreSQL
        async with AsyncSessionFactory() as session:
            saved_record = await persist_market_price(
                session,
                market_price,
            )

            print("\nRecord persisted successfully!")
            print("Database ID:", saved_record.id)
            print("Exchange ID:", saved_record.exchange_id)

            # 4. Read the record back from PostgreSQL
            repository = MarketDataRepository(session)

            db_record = await repository.get_latest_price(
                exchange_name="binance",
                symbol="BTCUSDT",
            )

            assert db_record is not None
            assert db_record.symbol == market_price.symbol
            assert db_record.price == market_price.price
            assert db_record.exchange_id == saved_record.exchange_id

            print("\nDatabase verification successful!")
            print("Saved symbol:", db_record.symbol)
            print("Saved price:", db_record.price)
            print("Fetched at:", db_record.fetched_at)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())