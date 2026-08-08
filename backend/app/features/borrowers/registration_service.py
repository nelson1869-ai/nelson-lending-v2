"""Transactional Borrower registration and review services."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.borrowers.registration_exceptions import RegistrationConflict
from app.features.borrowers.registration_models import BorrowerRegistration
from app.features.borrowers.registration_schemas import BorrowerRegistrationCreate
from app.features.borrowers.registration_validation import normalize_philippine_mobile

IDENTITY_CONFLICT_MESSAGE = (
    "A registration or borrower account already exists for the supplied identity."
)


async def create_registration(
    session: AsyncSession, payload: BorrowerRegistrationCreate
) -> BorrowerRegistration:
    """Store one pending registration while protecting existing identities."""

    normalized_phone = normalize_philippine_mobile(payload.phone_number)
    try:
        async with session.begin():
            existing_identity = await session.scalar(
                select(Borrower.id).where(Borrower.national_id == payload.national_id).limit(1)
            )
            existing_account = await session.scalar(
                select(BorrowerAccount.id)
                .where(BorrowerAccount.phone_number_normalized == normalized_phone)
                .limit(1)
            )
            existing_registration = await session.scalar(
                select(BorrowerRegistration.id)
                .where(
                    BorrowerRegistration.status == "pending",
                    or_(
                        BorrowerRegistration.national_id == payload.national_id,
                        BorrowerRegistration.phone_number_normalized == normalized_phone,
                    ),
                )
                .limit(1)
            )
            if existing_identity or existing_account or existing_registration:
                raise RegistrationConflict(IDENTITY_CONFLICT_MESSAGE)

            registration = BorrowerRegistration(
                first_name=payload.first_name,
                last_name=payload.last_name,
                national_id=payload.national_id,
                phone_number=payload.phone_number,
                phone_number_normalized=normalized_phone,
                address=payload.address,
                date_of_birth=payload.date_of_birth,
            )
            session.add(registration)
            await session.flush()
    except IntegrityError as exc:
        raise RegistrationConflict(IDENTITY_CONFLICT_MESSAGE) from exc
    return registration
