"""ORM model registry used by Alembic metadata discovery."""

from app.features.borrowers.activation_models import BorrowerActivationCode
from app.features.borrowers.models import (
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
)
from app.features.borrowers.registration_models import BorrowerRegistration
from app.features.business_settings.models import BusinessSetting
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.owner_identity.models import OwnerRefreshToken, OwnerUser
from app.features.payments.models import Payment

MODEL_REGISTRY = (
    OwnerUser,
    OwnerRefreshToken,
    Borrower,
    BorrowerAccount,
    BorrowerDevice,
    BorrowerRefreshToken,
    BorrowerActivationCode,
    BorrowerRegistration,
    BusinessSetting,
    Loan,
    LoanRequest,
    Payment,
)

