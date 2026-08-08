"""FastAPI application factory and ASGI entry point."""

import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings

APP_VERSION = "0.1.0"


def configure_logging(level: str) -> None:
    """Install a minimal process-wide logging baseline."""

    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app() -> FastAPI:
    """Build the API without opening a database connection."""

    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(title=settings.app_name, version=APP_VERSION)
    application.include_router(api_router)
    return application


app = create_app()
