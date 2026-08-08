"""Integration tests for loan lifecycle management APIs."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_security import create_borrower_access_token
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.loan_requests.models import LoanRequest
from app.features.owner_identity.service import bootstrap_owner, login_owner
from app.main import app

pytestmark = pytest.mark.integration

OWNER_LOANS_URL = "/api/v1/owner/loans"
BORROWER_LOANS_URL = "/api/v1/borrower/loans"
OWNER_PASS = "owner lifecycle pass 123"


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


async def setup_owner_token(
    db_session: AsyncSession, username: str = "owner_life"
) -> dict[str, str]:
    await bootstrap_owner(db_session, username=username, password=OWNER_PASS)
    pair = await login_owner(db_session, username=username, password=OWNER_PASS)
    return {"Authorization": f"Bearer {pair.access_token.value}"}


async def setup_borrower_token(
    db_session: AsyncSession,
    suffix: str = "301",
) -> tuple[dict[str, str], Borrower]:
    b = Borrower(
        first_name="Lifecycle",
        last_name=f"Borrower {suffix}",
        national_id=f"B-LIFE-ID-{suffix}",
        address="123 Lifecycle St",
        phone_number=f"0918{suffix:0>7}",
        phone_number_normalized=f"+63918{suffix:0>7}",
        date_of_birth=date(1992, 5, 15),
        status="active",
    )
    db_session.add(b)
    await db_session.flush()

    acct = BorrowerAccount(
        borrower_id=b.id,
        phone_number=b.phone_number,
        phone_number_normalized=b.phone_number_normalized,
        account_status="activated",
    )
    db_session.add(acct)
    await db_session.flush()

    token = create_borrower_access_token(acct.id, b.id)
    return {"Authorization": f"Bearer {token.value}"}, b


async def create_approved_request(
    db_session: AsyncSession,
    borrower_id: UUID,
    rate: str = "0.045",
) -> LoanRequest:
    today = date.today()
    first_due = (
        date(today.year, today.month, 15)
        if today.day < 15
        else date(today.year, today.month + 1, 15)
    )
    req = LoanRequest(
        borrower_id=borrower_id,
        requested_principal=Decimal("15000.00"),
        requested_monthly_rate=Decimal(rate),
        requested_term_months=6,
        requested_payment_frequency="twice_monthly",
        requested_first_due_date=first_due,
        status="approved",
        submitted_at=datetime.now(UTC),
        reviewed_at=datetime.now(UTC),
        owner_note="Approved for lifecycle test",
    )
    db_session.add(req)
    await db_session.flush()
    return req


async def test_convert_approved_request_to_loan_success(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session, "owner_conv_1")
    _, borrower = await setup_borrower_token(db_session, "301")
    request_record = await create_approved_request(db_session, borrower.id)

    res = await api_client.post(
        f"/api/v1/owner/loan-requests/{request_record.id}/create-loan",
        headers=owner_headers,
    )

    assert res.status_code == 201
    data = res.json()
    assert data["loanRequestId"] == str(request_record.id)
    assert data["borrowerId"] == str(borrower.id)
    assert data["originalPrincipal"] == "15000.00"
    assert data["outstandingPrincipal"] == "15000.00"
    assert Decimal(data["monthlyRate"]) == Decimal("0.045")

    assert data["status"] == "pending_disbursement"
    assert data["disbursedAt"] is None


async def test_convert_non_approved_request_fails(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session, "owner_conv_2")
    _, borrower = await setup_borrower_token(db_session, "302")

    pending_req = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal("10000.00"),
        requested_monthly_rate=Decimal("0.05"),
        requested_term_months=3,
        requested_payment_frequency="monthly",
        requested_first_due_date=date.today() + timedelta(days=30),
        status="pending",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(pending_req)
    await db_session.flush()

    res = await api_client.post(
        f"/api/v1/owner/loan-requests/{pending_req.id}/create-loan",
        headers=owner_headers,
    )

    assert res.status_code == 400
    assert "expected 'approved'" in res.json()["detail"]


async def test_duplicate_loan_creation_conflict(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session, "owner_conv_3")
    _, borrower = await setup_borrower_token(db_session, "303")
    request_record = await create_approved_request(db_session, borrower.id)

    res1 = await api_client.post(
        f"/api/v1/owner/loan-requests/{request_record.id}/create-loan",
        headers=owner_headers,
    )
    assert res1.status_code == 201

    res2 = await api_client.post(
        f"/api/v1/owner/loan-requests/{request_record.id}/create-loan",
        headers=owner_headers,
    )
    assert res2.status_code == 409
    assert "already been created" in res2.json()["detail"]


async def test_disburse_and_cancel_lifecycle_transitions(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session, "owner_lifecycle_1")
    _, borrower = await setup_borrower_token(db_session, "304")
    request1 = await create_approved_request(db_session, borrower.id)

    # Create Loan 1
    create_res1 = await api_client.post(
        f"/api/v1/owner/loan-requests/{request1.id}/create-loan",
        headers=owner_headers,
    )
    loan1_id = create_res1.json()["id"]

    # Disburse Loan 1
    disburse_res = await api_client.post(
        f"{OWNER_LOANS_URL}/{loan1_id}/disburse",
        headers=owner_headers,
    )
    assert disburse_res.status_code == 200
    disburse_data = disburse_res.json()
    assert disburse_data["status"] == "active"
    assert disburse_data["disbursedAt"] is not None

    # Cannot disburse active loan again
    disburse_again_res = await api_client.post(
        f"{OWNER_LOANS_URL}/{loan1_id}/disburse",
        headers=owner_headers,
    )
    assert disburse_again_res.status_code == 409

    # Cannot cancel active loan
    cancel_active_res = await api_client.post(
        f"{OWNER_LOANS_URL}/{loan1_id}/cancel",
        headers=owner_headers,
    )
    assert cancel_active_res.status_code == 409

    # Create Loan 2 to test cancellation
    request2 = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal("5000.00"),
        requested_monthly_rate=Decimal("0.04"),
        requested_term_months=3,
        requested_payment_frequency="monthly",
        requested_first_due_date=date.today() + timedelta(days=30),
        status="approved",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(request2)
    await db_session.flush()

    create_res2 = await api_client.post(
        f"/api/v1/owner/loan-requests/{request2.id}/create-loan",
        headers=owner_headers,
    )
    loan2_id = create_res2.json()["id"]

    # Cancel Loan 2
    cancel_res = await api_client.post(
        f"{OWNER_LOANS_URL}/{loan2_id}/cancel",
        headers=owner_headers,
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["status"] == "cancelled"
    assert cancel_data["cancelledAt"] is not None

    # Cannot disburse cancelled loan
    disburse_cancelled_res = await api_client.post(
        f"{OWNER_LOANS_URL}/{loan2_id}/disburse",
        headers=owner_headers,
    )
    assert disburse_cancelled_res.status_code == 409


async def test_owner_and_borrower_loan_visibility(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session, "owner_vis_1")
    b1_headers, borrower1 = await setup_borrower_token(db_session, "305")
    b2_headers, borrower2 = await setup_borrower_token(db_session, "306")

    req1 = await create_approved_request(db_session, borrower1.id)
    req2 = await create_approved_request(db_session, borrower2.id)

    # Convert requests into loans
    res1 = await api_client.post(
        f"/api/v1/owner/loan-requests/{req1.id}/create-loan",
        headers=owner_headers,
    )
    res2 = await api_client.post(
        f"/api/v1/owner/loan-requests/{req2.id}/create-loan",
        headers=owner_headers,
    )
    loan1_id = res1.json()["id"]
    loan2_id = res2.json()["id"]
    assert loan2_id != loan1_id

    # Owner can list all loans
    owner_list_res = await api_client.get(OWNER_LOANS_URL, headers=owner_headers)
    assert owner_list_res.status_code == 200
    owner_loans = owner_list_res.json()
    assert len(owner_loans) >= 2

    # Owner detail includes quote preview
    owner_detail_res = await api_client.get(
        f"{OWNER_LOANS_URL}/{loan1_id}",
        headers=owner_headers,
    )
    assert owner_detail_res.status_code == 200
    assert "quotePreview" in owner_detail_res.json()
    assert len(owner_detail_res.json()["quotePreview"]["schedule"]) > 0

    # Borrower 1 can list own loans (1 loan)
    b1_list_res = await api_client.get(BORROWER_LOANS_URL, headers=b1_headers)
    assert b1_list_res.status_code == 200
    b1_loans = b1_list_res.json()
    assert len(b1_loans) == 1
    assert b1_loans[0]["id"] == loan1_id

    # Borrower 1 detail view includes schedule preview
    b1_detail_res = await api_client.get(
        f"{BORROWER_LOANS_URL}/{loan1_id}",
        headers=b1_headers,
    )
    assert b1_detail_res.status_code == 200
    assert "quotePreview" in b1_detail_res.json()

    # Cross-borrower isolation: Borrower 2 cannot view Borrower 1's loan
    b2_cross_res = await api_client.get(
        f"{BORROWER_LOANS_URL}/{loan1_id}",
        headers=b2_headers,
    )
    assert b2_cross_res.status_code == 404

    # Role isolation: Borrower token rejected on Owner loan endpoints
    b1_on_owner_res = await api_client.get(OWNER_LOANS_URL, headers=b1_headers)
    assert b1_on_owner_res.status_code in (401, 403)

    # Role isolation: Owner token rejected on Borrower loan endpoints
    owner_on_b_res = await api_client.get(BORROWER_LOANS_URL, headers=owner_headers)
    assert owner_on_b_res.status_code in (401, 403)
