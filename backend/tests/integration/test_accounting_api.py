"""Integration tests for Owner accounting APIs and Borrower authorization privacy."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_owner_access_token, hash_password
from app.features.borrowers.auth_security import create_borrower_access_token, hash_pin
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.owner_identity.models import OwnerUser
from app.features.payments.schemas import PaymentPostRequest
from app.features.payments.service import post_payment


async def _owner_headers(db_session: AsyncSession) -> dict[str, str]:
    owner = OwnerUser(
        username=f"owner_{uuid4().hex[:6]}",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
    )
    db_session.add(owner)
    await db_session.flush()
    token = create_owner_access_token(owner.id)
    return {"Authorization": f"Bearer {token.value}"}


async def _borrower_headers(db_session: AsyncSession) -> dict[str, str]:
    borrower = Borrower(
        first_name="Auth",
        last_name="Test",
        national_id=f"NAT-AUTH-{uuid4().hex[:6]}",
        address="123 Auth St",
        phone_number=f"0917{uuid4().hex[:7]}",
        phone_number_normalized=f"+63917{uuid4().hex[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db_session.add(borrower)
    await db_session.flush()

    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("123456"),
    )
    db_session.add(account)
    await db_session.flush()

    token = create_borrower_access_token(account.id, borrower.id)
    return {"Authorization": f"Bearer {token.value}"}


async def test_owner_can_list_accounts(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Owner can retrieve the Chart of Accounts."""
    headers = await _owner_headers(db_session)
    response = await api_client.get("/api/v1/owner/accounting/accounts", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    codes = {acc["code"] for acc in data}
    assert {"1000", "1100", "2000", "4000"}.issubset(codes)


async def test_owner_can_list_and_get_journals(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Owner can list journals and fetch detail of a specific journal."""
    owner_hdr = await _owner_headers(db_session)

    # Post a payment to generate a journal
    borrower = Borrower(
        first_name="API",
        last_name="Test",
        national_id=f"NAT-API-{uuid4().hex[:6]}",
        address="API St",
        phone_number=f"0919{uuid4().hex[:7]}",
        phone_number_normalized=f"+63919{uuid4().hex[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db_session.add(borrower)
    await db_session.flush()

    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal("1000.00"),
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_monthly_rate=Decimal("0.10"),
        requested_first_due_date=date(2026, 6, 15),
        status="approved",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(request)
    await db_session.flush()

    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=Decimal("1000.00"),
        outstanding_principal=Decimal("1000.00"),
        monthly_rate=Decimal("0.10"),
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 6, 15),
        final_due_date=date(2026, 6, 15),
        next_interest_due_date=date(2026, 6, 15),
        status="active",
        disbursed_at=datetime(2026, 5, 15, tzinfo=UTC),
        accrued_interest=Decimal("0.00"),
    )
    db_session.add(loan)
    await db_session.flush()

    key = f"api-key-{uuid4().hex[:6]}"
    await post_payment(
        db_session,
        loan.id,
        PaymentPostRequest(amount=Decimal("500.00"), payment_date=date(2026, 6, 15)),
        idempotency_key=key,
    )
    await db_session.commit()

    # GET /journals
    list_res = await api_client.get("/api/v1/owner/accounting/journals", headers=owner_hdr)
    assert list_res.status_code == 200
    journals = list_res.json()
    assert len(journals) >= 1
    target = journals[0]
    j_id = target["id"]

    # GET /journals/{j_id}
    detail_res = await api_client.get(
        f"/api/v1/owner/accounting/journals/{j_id}", headers=owner_hdr
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == j_id
    assert detail["is_balanced"] is True
    assert detail["total_debit"] == detail["total_credit"]

    # POST /journals/{j_id}/reverse
    rev_res = await api_client.post(
        f"/api/v1/owner/accounting/journals/{j_id}/reverse",
        headers=owner_hdr,
        json={"reason": "Customer duplicate payment"},
    )
    assert rev_res.status_code == 201
    rev_data = rev_res.json()
    assert rev_data["reversal_of_id"] == j_id
    assert rev_data["event_type"] == "reversal"


async def test_borrower_cannot_access_accounting_endpoints(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Borrowers are unauthorized to access internal accounting endpoints."""
    borrower_hdr = await _borrower_headers(db_session)

    res1 = await api_client.get("/api/v1/owner/accounting/accounts", headers=borrower_hdr)
    assert res1.status_code in (401, 403)

    res2 = await api_client.get("/api/v1/owner/accounting/journals", headers=borrower_hdr)
    assert res2.status_code in (401, 403)


async def test_unauthenticated_cannot_access_accounting_endpoints(
    api_client: AsyncClient,
) -> None:
    """Unauthenticated requests are rejected."""
    res = await api_client.get("/api/v1/owner/accounting/accounts")
    assert res.status_code == 401
