"""ORM model registry used by Alembic metadata discovery."""

from app.features.borrowers.models import (
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
)
from app.features.business_settings.models import BusinessSetting
from app.features.owner_identity.models import OwnerRefreshToken, OwnerUser

MODEL_REGISTRY = (
    OwnerUser,
    OwnerRefreshToken,
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
    BusinessSetting,
)
