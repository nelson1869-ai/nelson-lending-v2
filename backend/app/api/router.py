"""Single composition point for application API routes."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.core.config import get_settings
from app.features.borrowers.registration_router import public_router as borrower_registration_router
from app.features.owner_identity.router import router as owner_auth_router

api_router = APIRouter()
versioned_router = APIRouter()
versioned_router.include_router(borrower_registration_router)
versioned_router.include_router(owner_auth_router)

api_router.include_router(health_router)
api_router.include_router(versioned_router, prefix=get_settings().api_v1_prefix)
