"""Transactional Borrower registration and Owner review services."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.borrowers.registration_exceptions import (
    RegistrationConflict,
    RegistrationNotFound,
    RegistrationStateConflict,
)
from app.features.borrowers.registration_models import BorrowerRegistration
from app.features.borrowers.registration_schemas import BorrowerRegistrationCreate
from app.features.borrowers.registration_validation import normalize_philippine_mobile

IDENTITY_CONFLICT_MESSAGE = (
    "A registration or borrower account already exists for the supplied identity."
)
STATE_CONFLICT_MESSAGE = "Registration has already received a terminal decision."


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


async def list_registrations(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[BorrowerRegistration], int]:
    """Return pending registrations oldest-first with a bounded total."""

    conditions = (BorrowerRegistration.status == "pending",)
    total = await session.scalar(
        select(func.count()).select_from(BorrowerRegistration).where(*conditions)
    )
    records = await session.scalars(
        select(BorrowerRegistration)
        .where(*conditions)
        .order_by(BorrowerRegistration.submitted_at, BorrowerRegistration.id)
        .limit(limit)
        .offset(offset)
    )
    return list(records), total or 0


async def get_registration(session: AsyncSession, registration_id: UUID) -> BorrowerRegistration:
    """Load one registration for Owner review."""

    registration = await session.get(BorrowerRegistration, registration_id)
    if registration is None:
        raise RegistrationNotFound("Registration not found")
    return registration


async def _locked_pending_registration(
    session: AsyncSession, registration_id: UUID
) -> BorrowerRegistration:
    registration = await session.scalar(
        select(BorrowerRegistration)
        .where(BorrowerRegistration.id == registration_id)
        .with_for_update()
    )
    if registration is None:
        raise RegistrationNotFound("Registration not found")
    if registration.status != "pending":
        raise RegistrationStateConflict(STATE_CONFLICT_MESSAGE)
    return registration


async def approve_registration(
    session: AsyncSession, *, registration_id: UUID, owner_id: UUID
) -> BorrowerRegistration:
    """Atomically create the business identity/account and approve one locked request."""

    try:
        registration = await _locked_pending_registration(session, registration_id)
        existing_borrower = await session.scalar(
            select(Borrower.id).where(Borrower.national_id == registration.national_id).limit(1)
        )
        existing_account = await session.scalar(
            select(BorrowerAccount.id)
            .where(BorrowerAccount.phone_number_normalized == registration.phone_number_normalized)
            .limit(1)
        )
        if existing_borrower or existing_account:
            raise RegistrationConflict(IDENTITY_CONFLICT_MESSAGE)

        borrower = Borrower(
            first_name=registration.first_name,
            last_name=registration.last_name,
            national_id=registration.national_id,
            address=registration.address,
            phone_number=registration.phone_number,
            phone_number_normalized=registration.phone_number_normalized,
            date_of_birth=registration.date_of_birth,
            status="active",
        )
        session.add(borrower)
        await session.flush()
        account = BorrowerAccount(
            borrower_id=borrower.id,
            phone_number=registration.phone_number,
            phone_number_normalized=registration.phone_number_normalized,
            account_status="approved",
            pin_hash=None,
        )
        session.add(account)
        await session.flush()

        registration.status = "approved"
        registration.reviewed_at = datetime.now(UTC)
        registration.reviewed_by_owner_user_id = owner_id
        registration.borrower_id = borrower.id
        registration.rejection_reason = None
        await session.commit()
        return registration
    except (RegistrationConflict, RegistrationNotFound, RegistrationStateConflict):
        await session.rollback()
        raise
    except IntegrityError as exc:
        await session.rollback()
        raise RegistrationConflict(IDENTITY_CONFLICT_MESSAGE) from exc
    except Exception:
        await session.rollback()
        raise


async def reject_registration(
    session: AsyncSession, *, registration_id: UUID, owner_id: UUID, reason: str
) -> BorrowerRegistration:
    """Atomically reject one locked pending registration without creating identities."""

    try:
        registration = await _locked_pending_registration(session, registration_id)
        registration.status = "rejected"
        registration.reviewed_at = datetime.now(UTC)
        registration.reviewed_by_owner_user_id = owner_id
        registration.rejection_reason = reason
        await session.commit()
        return registration
    except (RegistrationNotFound, RegistrationStateConflict):
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
