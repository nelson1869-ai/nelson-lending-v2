"""Borrower registration lifecycle against the dedicated local PostgreSQL database."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.session import get_db
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.borrowers.registration_exceptions import RegistrationStateConflict
from app.features.borrowers.registration_models import BorrowerRegistration
from app.features.borrowers.registration_schemas import BorrowerRegistrationCreate
from app.features.borrowers.registration_service import approve_registration
from app.features.owner_identity.models import OwnerUser
from app.features.owner_identity.service import bootstrap_owner, login_owner
from app.main import app

pytestmark = pytest.mark.integration

OWNER_PASSWORD = "registration owner password"
PUBLIC_URL = "/api/v1/borrower/registrations"
OWNER_URL = "/api/v1/owner/borrower-registrations"


def registration_payload(suffix: int = 1, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "firstName": "Juan",
        "lastName": f"Dela Cruz {suffix}",
        "nationalId": f"SYNTH-ID-{suffix:07d}",
        "phoneNumber": f"0917{suffix:07d}",
        "address": "Synthetic Bacolod test address",
        "dateOfBirth": "1995-05-10",
    }
    values.update(overrides)
    return values


@pytest.fixture
async def registration_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def owner_headers(db_session: AsyncSession) -> dict[str, str]:
    owner = await bootstrap_owner(
        db_session, username="registration-owner", password=OWNER_PASSWORD
    )
    pair = await login_owner(db_session, username=owner.username, password=OWNER_PASSWORD)
    return {"Authorization": f"Bearer {pair.access_token.value}"}


async def submit(client: AsyncClient, suffix: int = 1, **overrides: object):
    return await client.post(PUBLIC_URL, json=registration_payload(suffix, **overrides))


async def test_public_registration_accepts_and_normalizes_phone(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    response = await submit(registration_client, phoneNumber="639171234567")
    registration = await db_session.get(
        BorrowerRegistration, UUID(response.json()["registrationId"])
    )

    assert response.status_code == 201
    assert set(response.json()) == {"registrationId", "status", "submittedAt", "message"}
    assert registration is not None
    assert registration.phone_number_normalized == "+639171234567"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phoneNumber", "123"),
        ("firstName", "   "),
        ("nationalId", "   "),
        ("dateOfBirth", str(date.today())),
    ],
)
async def test_public_registration_rejects_invalid_input(
    registration_client: AsyncClient, field: str, value: str
) -> None:
    response = await submit(registration_client, **{field: value})

    assert response.status_code == 422


@pytest.mark.parametrize("duplicate_field", ["nationalId", "phoneNumber"])
async def test_duplicate_pending_identity_is_generic_conflict(
    registration_client: AsyncClient, duplicate_field: str
) -> None:
    first_payload = registration_payload(10)
    assert (await registration_client.post(PUBLIC_URL, json=first_payload)).status_code == 201
    second_payload = registration_payload(11)
    second_payload[duplicate_field] = first_payload[duplicate_field]

    response = await registration_client.post(PUBLIC_URL, json=second_payload)

    assert response.status_code == 409
    assert response.json()["detail"].startswith("A registration or borrower account")
    assert "Juan" not in response.text


async def test_existing_borrower_national_id_is_conflict(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    payload = registration_payload(20)
    db_session.add(
        Borrower(
            first_name="Existing",
            last_name="Borrower",
            national_id=payload["nationalId"],
            address="Synthetic existing address",
            phone_number="09179999999",
            phone_number_normalized="+639179999999",
            date_of_birth=date(1990, 1, 1),
            status="active",
        )
    )
    await db_session.commit()

    response = await registration_client.post(PUBLIC_URL, json=payload)

    assert response.status_code == 409


async def test_existing_account_phone_is_conflict(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    borrower = Borrower(
        first_name="Existing",
        last_name="Account",
        national_id="SYNTH-EXISTING-ACCOUNT",
        address="Synthetic existing address",
        phone_number="09178888888",
        phone_number_normalized="+639178888888",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db_session.add(borrower)
    await db_session.flush()
    db_session.add(
        BorrowerAccount(
            borrower_id=borrower.id,
            phone_number="09170000030",
            phone_number_normalized="+639170000030",
            account_status="approved",
        )
    )
    await db_session.commit()

    response = await submit(registration_client, 30)

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("GET", OWNER_URL, None),
        ("GET", f"{OWNER_URL}/{uuid4()}", None),
        ("POST", f"{OWNER_URL}/{uuid4()}/approve", None),
        ("POST", f"{OWNER_URL}/{uuid4()}/reject", {"reason": "Synthetic rejection reason"}),
    ],
)
async def test_owner_review_routes_require_authentication(
    registration_client: AsyncClient, method: str, path: str, json_body: dict[str, str] | None
) -> None:
    response = await registration_client.request(method, path, json=json_body)

    assert response.status_code == 401


async def test_refresh_token_cannot_authorize_review(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    owner = await bootstrap_owner(db_session, username="owner", password=OWNER_PASSWORD)
    pair = await login_owner(db_session, username=owner.username, password=OWNER_PASSWORD)

    response = await registration_client.get(
        OWNER_URL, headers={"Authorization": f"Bearer {pair.refresh_token}"}
    )

    assert response.status_code == 401


async def test_malformed_access_token_cannot_authorize_review(
    registration_client: AsyncClient,
) -> None:
    response = await registration_client.get(
        OWNER_URL, headers={"Authorization": "Bearer malformed-token"}
    )

    assert response.status_code == 401


async def test_approval_creates_linked_pre_activation_identity(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    headers = await owner_headers(db_session)
    created = await submit(registration_client, 40)
    registration_id = created.json()["registrationId"]

    response = await registration_client.post(
        f"{OWNER_URL}/{registration_id}/approve", headers=headers
    )
    registration = await db_session.get(BorrowerRegistration, UUID(registration_id))
    borrower = await db_session.scalar(
        select(Borrower).where(Borrower.id == registration.borrower_id)
    )
    account = await db_session.scalar(
        select(BorrowerAccount).where(BorrowerAccount.borrower_id == borrower.id)
    )

    assert response.status_code == 200
    assert registration.status == "approved"
    assert registration.reviewed_at is not None
    assert registration.reviewed_by_owner_user_id is not None
    assert registration.borrower_id is not None
    assert borrower.status == "active"
    assert borrower.national_id == "SYNTH-ID-0000040"
    assert account.account_status == "approved"
    assert account.phone_number_normalized == "+639170000040"
    assert account.pin_hash is None


@pytest.mark.parametrize("follow_up", ["approve", "reject"])
async def test_approved_registration_is_terminal(
    db_session: AsyncSession, registration_client: AsyncClient, follow_up: str
) -> None:
    headers = await owner_headers(db_session)
    registration_id = (await submit(registration_client, 50)).json()["registrationId"]
    assert (
        await registration_client.post(f"{OWNER_URL}/{registration_id}/approve", headers=headers)
    ).status_code == 200

    response = await registration_client.post(
        f"{OWNER_URL}/{registration_id}/{follow_up}",
        headers=headers,
        json={"reason": "Synthetic rejection reason"} if follow_up == "reject" else None,
    )

    assert response.status_code == 409


async def test_rejection_records_review_without_creating_identity(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    headers = await owner_headers(db_session)
    registration_id = (await submit(registration_client, 60)).json()["registrationId"]

    response = await registration_client.post(
        f"{OWNER_URL}/{registration_id}/reject",
        headers=headers,
        json={"reason": "  Unable to verify synthetic information.  "},
    )
    registration = await db_session.get(BorrowerRegistration, UUID(registration_id))

    assert response.status_code == 200
    assert registration.status == "rejected"
    assert registration.rejection_reason == "Unable to verify synthetic information."
    assert registration.reviewed_at is not None
    assert registration.reviewed_by_owner_user_id is not None
    assert await db_session.scalar(select(func.count()).select_from(Borrower)) == 0
    assert await db_session.scalar(select(func.count()).select_from(BorrowerAccount)) == 0


@pytest.mark.parametrize("follow_up", ["reject", "approve"])
async def test_rejected_registration_is_terminal(
    db_session: AsyncSession, registration_client: AsyncClient, follow_up: str
) -> None:
    headers = await owner_headers(db_session)
    registration_id = (await submit(registration_client, 70)).json()["registrationId"]
    assert (
        await registration_client.post(
            f"{OWNER_URL}/{registration_id}/reject",
            headers=headers,
            json={"reason": "Synthetic rejection reason"},
        )
    ).status_code == 200

    response = await registration_client.post(
        f"{OWNER_URL}/{registration_id}/{follow_up}",
        headers=headers,
        json={"reason": "Another synthetic reason"} if follow_up == "reject" else None,
    )

    assert response.status_code == 409


async def test_pending_list_detail_and_pagination(
    db_session: AsyncSession, registration_client: AsyncClient
) -> None:
    headers = await owner_headers(db_session)
    first_id = (await submit(registration_client, 80)).json()["registrationId"]
    second_id = (await submit(registration_client, 81)).json()["registrationId"]
    await registration_client.post(
        f"{OWNER_URL}/{second_id}/reject",
        headers=headers,
        json={"reason": "Synthetic rejection reason"},
    )

    listing = await registration_client.get(f"{OWNER_URL}?limit=1&offset=0", headers=headers)
    detail = await registration_client.get(f"{OWNER_URL}/{first_id}", headers=headers)
    unknown = await registration_client.get(f"{OWNER_URL}/{uuid4()}", headers=headers)
    unbounded = await registration_client.get(f"{OWNER_URL}?limit=101", headers=headers)

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert [item["id"] for item in listing.json()["items"]] == [first_id]
    assert detail.status_code == 200
    assert detail.json()["nationalId"] == "SYNTH-ID-0000080"
    assert unknown.status_code == 404
    assert unbounded.status_code == 422


async def _cleanup_committed_flow(engine: AsyncEngine, owner_id: UUID) -> None:
    async with AsyncSession(engine) as session, session.begin():
        borrower_ids = list(
            await session.scalars(
                select(BorrowerRegistration.borrower_id).where(
                    BorrowerRegistration.reviewed_by_owner_user_id == owner_id,
                    BorrowerRegistration.borrower_id.is_not(None),
                )
            )
        )
        await session.execute(
            delete(BorrowerRegistration).where(
                BorrowerRegistration.reviewed_by_owner_user_id == owner_id
            )
        )
        if borrower_ids:
            await session.execute(
                delete(BorrowerAccount).where(BorrowerAccount.borrower_id.in_(borrower_ids))
            )
            await session.execute(delete(Borrower).where(Borrower.id.in_(borrower_ids)))
        await session.execute(delete(OwnerUser).where(OwnerUser.id == owner_id))


async def test_concurrent_approval_allows_exactly_one_transition(
    integration_engine: AsyncEngine,
) -> None:
    async with AsyncSession(integration_engine, expire_on_commit=False) as seed:
        owner = await bootstrap_owner(seed, username="concurrency-owner", password=OWNER_PASSWORD)
        payload = BorrowerRegistrationCreate.model_validate(registration_payload(90))
        registration = BorrowerRegistration(
            first_name=payload.first_name,
            last_name=payload.last_name,
            national_id=payload.national_id,
            phone_number=payload.phone_number,
            phone_number_normalized="+639170000090",
            address=payload.address,
            date_of_birth=payload.date_of_birth,
        )
        seed.add(registration)
        await seed.commit()
        owner_id, registration_id = owner.id, registration.id

    async def attempt() -> str:
        async with AsyncSession(integration_engine) as session:
            try:
                await approve_registration(
                    session, registration_id=registration_id, owner_id=owner_id
                )
                return "approved"
            except RegistrationStateConflict:
                return "conflict"

    try:
        results = await asyncio.gather(attempt(), attempt())
        assert sorted(results) == ["approved", "conflict"]
        async with AsyncSession(integration_engine) as verify:
            assert (
                await verify.scalar(
                    select(func.count())
                    .select_from(Borrower)
                    .where(Borrower.national_id == payload.national_id)
                )
                == 1
            )
            assert (
                await verify.scalar(
                    select(func.count())
                    .select_from(BorrowerAccount)
                    .where(BorrowerAccount.phone_number_normalized == "+639170000090")
                )
                == 1
            )
    finally:
        await _cleanup_committed_flow(integration_engine, owner_id)


async def test_account_creation_failure_rolls_back_borrower_and_decision(
    integration_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with AsyncSession(integration_engine, expire_on_commit=False) as seed:
        owner = await bootstrap_owner(seed, username="rollback-owner", password=OWNER_PASSWORD)
        payload = BorrowerRegistrationCreate.model_validate(registration_payload(91))
        registration = BorrowerRegistration(
            first_name=payload.first_name,
            last_name=payload.last_name,
            national_id=payload.national_id,
            phone_number=payload.phone_number,
            phone_number_normalized="+639170000091",
            address=payload.address,
            date_of_birth=payload.date_of_birth,
        )
        seed.add(registration)
        await seed.commit()
        owner_id, registration_id = owner.id, registration.id

    try:
        async with AsyncSession(integration_engine) as session:
            original_flush = session.flush
            flush_count = 0

            async def fail_account_flush(objects: object = None) -> None:
                nonlocal flush_count
                flush_count += 1
                if flush_count == 2:
                    raise RuntimeError("synthetic account flush failure")
                await original_flush(objects)

            monkeypatch.setattr(session, "flush", fail_account_flush)
            with pytest.raises(RuntimeError, match="synthetic account flush failure"):
                await approve_registration(
                    session, registration_id=registration_id, owner_id=owner_id
                )

        async with AsyncSession(integration_engine) as verify:
            persisted = await verify.get(BorrowerRegistration, registration_id)
            assert persisted is not None
            assert persisted.status == "pending"
            assert persisted.borrower_id is None
            assert (
                await verify.scalar(
                    select(func.count())
                    .select_from(Borrower)
                    .where(Borrower.national_id == payload.national_id)
                )
                == 0
            )
            assert (
                await verify.scalar(
                    select(func.count())
                    .select_from(BorrowerAccount)
                    .where(BorrowerAccount.phone_number_normalized == "+639170000091")
                )
                == 0
            )
    finally:
        async with AsyncSession(integration_engine) as cleanup, cleanup.begin():
            await cleanup.execute(
                delete(BorrowerRegistration).where(BorrowerRegistration.id == registration_id)
            )
            await cleanup.execute(delete(OwnerUser).where(OwnerUser.id == owner_id))
