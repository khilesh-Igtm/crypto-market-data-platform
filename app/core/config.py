from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide configuration.
    """

    app_name: str = "Crypto Market Data Platform"

    app_env: Literal[
        "local",
        "development",
        "staging",
        "production",
    ] = "local"

    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "crypto_market_data"
    database_user: str = "crypto_app"
    database_password: SecretStr

    redis_url: str = "redis://localhost:6379/0"
    latest_price_cache_ttl: int = 5
    history_cache_ttl: int = 60

    # Background ingestion configuration
    ingestion_symbols: str = "BTCUSDT,ETHUSDT"
    ingestion_poll_interval_seconds: float = Field(
        default=5.0,
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()