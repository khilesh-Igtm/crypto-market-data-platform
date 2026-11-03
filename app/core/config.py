from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide configuration.

    Values are loaded from environment variables
    or the local .env file.
    """

    app_name: str = "Crypto Market Data Platform"

    app_env: Literal[
        "local",
        "development",
        "staging",
        "production"
    ] = "local"

    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    # Database configuration yahan aayega (class ke andar)
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "crypto_market_data"
    database_user: str = "crypto_app"
    database_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return cached application settings.
    """
    return Settings()