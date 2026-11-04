from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application.
    """

    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_app()