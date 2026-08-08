"""Single composition point for application API routes."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.core.config import get_settings

api_router = APIRouter()
versioned_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(versioned_router, prefix=get_settings().api_v1_prefix)
