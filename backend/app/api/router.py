"""Single composition point for application API routes."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.core.config import get_settings
from app.features.borrowers.auth_router import borrower_router as borrower_auth_router
from app.features.borrowers.auth_router import owner_router as owner_activation_router
from app.features.borrowers.registration_router import (
    owner_router as owner_borrower_registration_router,
)
from app.features.borrowers.registration_router import (
    public_router as borrower_registration_router,
)
from app.features.loan_requests.router import (
    borrower_loan_requests_router,
    owner_loan_requests_router,
)
from app.features.loans.router import router as owner_loans_router
from app.features.owner_identity.router import router as owner_auth_router

api_router = APIRouter()
versioned_router = APIRouter()
versioned_router.include_router(borrower_registration_router)
versioned_router.include_router(owner_borrower_registration_router)
versioned_router.include_router(owner_auth_router)
versioned_router.include_router(owner_activation_router)
versioned_router.include_router(borrower_auth_router)
versioned_router.include_router(owner_loans_router)
versioned_router.include_router(borrower_loan_requests_router)
versioned_router.include_router(owner_loan_requests_router)

api_router.include_router(health_router)
api_router.include_router(versioned_router, prefix=get_settings().api_v1_prefix)
