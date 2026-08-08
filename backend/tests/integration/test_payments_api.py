"""Integration tests for payment posting, canonical allocation, and history endpoints."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_owner_access_token, hash_password
from app.features.borrowers.auth_security import create_borrower_access_token, hash_pin
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.owner_identity.models import OwnerUser
from app.features.payments.models import Payment

pytestmark = pytest.mark.integration


async def setup_owner_and_headers(session: AsyncSession) -> dict[str, str]:
    """Helper to register an Owner and return bearer auth headers."""
    owner = OwnerUser(
        username=f"owner-{uuid4().hex[:6]}",
        password_hash=hash_password("OwnerPassword123!"),
        is_active=True,
    )
    session.add(owner)
    await session.flush()

    token = create_owner_access_token(owner.id)
    return {"Authorization": f"Bearer {token.value}"}


async def setup_borrower_and_headers(
    session: AsyncSession,
) -> tuple[BorrowerAccount, dict[str, str]]:
    """Helper to register an active Borrower with PIN and return (account, auth headers)."""
    suffix = uuid4().hex[:6]
    borrower = Borrower(
        first_name="Borrower",
        last_name="Test",
        national_id=f"NAT-{suffix}",
        address="123 Test St",
        phone_number=f"0918{suffix[:7]}",
        phone_number_normalized=f"+63918{suffix[:7]}",
        date_of_birth=date(1995, 5, 5),
        status="active",
    )
    session.add(borrower)
    await session.flush()

    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("123456"),
    )
    session.add(account)
    await session.flush()

    token = create_borrower_access_token(account.id, borrower.id)
    return account, {"Authorization": f"Bearer {token.value}"}


async def setup_active_loan(
    session: AsyncSession,
    borrower_id: UUID,
    principal: Decimal = Decimal("2000.00"),
    monthly_rate: Decimal = Decimal("0.10"),
    status: str = "active",
) -> Loan:
    """Helper to setup an approved request and loan in session."""
    request = LoanRequest(
        borrower_id=borrower_id,
        requested_principal=principal,
        requested_term_months=1,
        requested_payment_frequency="monthly",
        requested_monthly_rate=monthly_rate,
        requested_first_due_date=date(2026, 9, 15),
        status="approved",
        submitted_at=datetime.now(UTC),
    )

    session.add(request)
    await session.flush()

    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower_id,
        original_principal=principal,
        outstanding_principal=principal,
        monthly_rate=monthly_rate,
        term_months=1,
        payment_frequency="monthly",
        number_of_payments=1,
        first_due_date=date(2026, 9, 15),
        final_due_date=date(2026, 9, 15),
        status=status,
        disbursed_at=datetime.now(UTC) if status == "active" else None,
        accrued_interest=Decimal("0.00"),
    )
    session.add(loan)
    await session.flush()
    return loan


async def test_case_a_exact_interest_payment(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # ₱2,000 principal @ 10% monthly = ₱200 interest due. Payment = ₱200.
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={
            "amount": "200.00",
            "payment_date": "2026-09-15",
            "reference": "REF-CASE-A",
            "note": "Exact interest payment",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "200.00"
    assert data["interest_paid"] == "200.00"
    assert data["principal_paid"] == "0.00"
    assert data["remaining_interest"] == "0.00"
    assert data["remaining_principal"] == "2000.00"
    assert data["unapplied_credit"] == "0.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("2000.00")
    assert loan.status == "active"


async def test_case_b_interest_and_principal_reduction(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # ₱2,000 principal @ 10% monthly = ₱200 interest due. Payment = ₱700.
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={
            "amount": "700.00",
            "payment_date": "2026-09-15",
            "reference": "REF-CASE-B",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "700.00"
    assert data["interest_paid"] == "200.00"
    assert data["principal_paid"] == "500.00"
    assert data["remaining_interest"] == "0.00"
    assert data["remaining_principal"] == "1500.00"
    assert data["unapplied_credit"] == "0.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("1500.00")
    assert loan.status == "active"


async def test_case_c_payoff_with_overpayment(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # ₱2,000 principal @ 10% monthly = ₱200 interest due. Payment = ₱2,500.
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={
            "amount": "2500.00",
            "payment_date": "2026-09-15",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "2500.00"
    assert data["interest_paid"] == "200.00"
    assert data["principal_paid"] == "2000.00"
    assert data["remaining_interest"] == "0.00"
    assert data["remaining_principal"] == "0.00"
    assert data["unapplied_credit"] == "300.00"

    await db_session.refresh(loan)
    assert loan.outstanding_principal == Decimal("0.00")
    assert loan.status == "paid"
    assert loan.paid_at is not None


async def test_partial_interest_payment(api_client: AsyncClient, db_session: AsyncSession) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # ₱2,000 principal @ 10% monthly = ₱200 interest due. Payment = ₱100.
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={
            "amount": "100.00",
            "payment_date": "2026-09-15",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "100.00"
    assert data["interest_paid"] == "100.00"
    assert data["principal_paid"] == "0.00"
    assert data["remaining_interest"] == "100.00"
    assert data["remaining_principal"] == "2000.00"
    assert data["unapplied_credit"] == "0.00"


async def test_subsequent_interest_on_reduced_principal(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # First payment: ₱700 (reduces principal to ₱1,500)
    await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "700.00", "payment_date": "2026-09-15"},
    )

    # Second payment: Next 10% monthly interest on ₱1,500 = ₱150.00. Payment = ₱150.00
    res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "150.00", "payment_date": "2026-10-15"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "150.00"
    assert data["interest_paid"] == "150.00"
    assert data["principal_paid"] == "0.00"
    assert data["remaining_principal"] == "1500.00"


async def test_multiple_payments_sequence(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)
    loan = await setup_active_loan(db_session, account.borrower_id)

    # Payment 1: ₱500 (₱200 interest, ₱300 principal -> ₱1700 remaining)
    p1 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "payment_date": "2026-09-15"},
    )
    assert p1.json()["remaining_principal"] == "1700.00"

    # Payment 2: ₱500 (10% of 1700 = ₱170 interest, ₱330 principal -> ₱1370 remaining)
    p2 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "payment_date": "2026-10-15"},
    )
    assert p2.json()["interest_paid"] == "170.00"
    assert p2.json()["principal_paid"] == "330.00"
    assert p2.json()["remaining_principal"] == "1370.00"

    # Payment 3: Payoff ₱1370 principal + 10% of 1370 (₱137) = ₱1507.00
    p3 = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={"amount": "1507.00", "payment_date": "2026-11-15"},
    )
    assert p3.json()["interest_paid"] == "137.00"
    assert p3.json()["principal_paid"] == "1370.00"
    assert p3.json()["remaining_principal"] == "0.00"

    await db_session.refresh(loan)
    assert loan.status == "paid"


async def test_invalid_loan_status_rejections(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account, _ = await setup_borrower_and_headers(db_session)

    # Pending loan
    pending_loan = await setup_active_loan(
        db_session, account.borrower_id, status="pending_disbursement"
    )
    res1 = await api_client.post(
        f"/api/v1/owner/loans/{pending_loan.id}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "payment_date": "2026-09-15"},
    )
    assert res1.status_code == 400
    assert "pending_disbursement" in res1.json()["detail"]

    # Cancelled loan
    cancelled_loan = await setup_active_loan(db_session, account.borrower_id, status="cancelled")
    res2 = await api_client.post(
        f"/api/v1/owner/loans/{cancelled_loan.id}/payments",
        headers=owner_headers,
        json={"amount": "500.00", "payment_date": "2026-09-15"},
    )
    assert res2.status_code == 400
    assert "cancelled" in res2.json()["detail"]


async def test_owner_and_borrower_payment_history_visibility(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    owner_headers = await setup_owner_and_headers(db_session)
    account_a, borrower_a_headers = await setup_borrower_and_headers(db_session)
    _, borrower_b_headers = await setup_borrower_and_headers(db_session)

    loan = await setup_active_loan(db_session, account_a.borrower_id)

    # Post payment as Owner
    await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
        json={
            "amount": "500.00",
            "payment_date": "2026-09-15",
            "reference": "REF-VISIBILITY",
            "note": "Private owner note",
        },
    )

    # Owner list payments -> includes note
    owner_res = await api_client.get(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=owner_headers,
    )
    assert owner_res.status_code == 200
    owner_data = owner_res.json()
    assert len(owner_data) == 1
    assert owner_data[0]["note"] == "Private owner note"

    # Borrower A (owner of loan) list payments -> succeeds, note omitted
    borrower_res = await api_client.get(
        f"/api/v1/borrower/loans/{loan.id}/payments",
        headers=borrower_a_headers,
    )
    assert borrower_res.status_code == 200
    borrower_data = borrower_res.json()
    assert len(borrower_data) == 1
    assert "note" not in borrower_data[0]
    assert borrower_data[0]["reference"] == "REF-VISIBILITY"

    # Borrower B (different borrower) list payments -> 404 Not Found (privacy boundary)
    other_borrower_res = await api_client.get(
        f"/api/v1/borrower/loans/{loan.id}/payments",
        headers=borrower_b_headers,
    )
    assert other_borrower_res.status_code == 404

    # Borrower cannot post payment on Owner route
    borrower_post_res = await api_client.post(
        f"/api/v1/owner/loans/{loan.id}/payments",
        headers=borrower_a_headers,
        json={"amount": "500.00", "payment_date": "2026-09-15"},
    )
    assert borrower_post_res.status_code in (401, 403)


async def test_concurrent_payment_row_locking(
    integration_engine, safe_test_database_url: str
) -> None:
    """Verify concurrent payment posts serialize cleanly via SELECT ... FOR UPDATE."""
    SessionMaker = async_sessionmaker(integration_engine, expire_on_commit=False)

    async with SessionMaker() as session:
        borrower = Borrower(
            first_name="Concurrent",
            last_name="Payer",
            national_id=f"NAT-CONC-{uuid4().hex[:6]}",
            address="Concurrent St",
            phone_number=f"0919{uuid4().hex[:7]}",
            phone_number_normalized=f"+63919{uuid4().hex[:7]}",
            date_of_birth=date(1990, 1, 1),
            status="active",
        )
        session.add(borrower)
        await session.flush()

        request = LoanRequest(
            borrower_id=borrower.id,
            requested_principal=Decimal("1000.00"),
            requested_term_months=1,
            requested_payment_frequency="monthly",
            requested_monthly_rate=Decimal("0.10"),
            requested_first_due_date=date(2026, 9, 15),
            status="approved",
            submitted_at=datetime.now(UTC),
        )

        session.add(request)
        await session.flush()

        loan = Loan(
            loan_request_id=request.id,
            borrower_id=borrower.id,
            original_principal=Decimal("1000.00"),
            outstanding_principal=Decimal("1000.00"),
            monthly_rate=Decimal("0.10"),
            term_months=1,
            payment_frequency="monthly",
            number_of_payments=1,
            first_due_date=date(2026, 9, 15),
            final_due_date=date(2026, 9, 15),
            status="active",
            disbursed_at=datetime.now(UTC),
        )
        session.add(loan)
        await session.flush()
        loan_id = loan.id
        borrower_id = borrower.id
        request_id = request.id
        await session.commit()

    try:
        from app.features.payments.schemas import PaymentPostRequest
        from app.features.payments.service import post_payment

        async def post_one(amt: str) -> None:
            async with SessionMaker() as s:
                await post_payment(
                    s,
                    loan_id,
                    PaymentPostRequest(
                        amount=Decimal(amt),
                        payment_date=date(2026, 9, 15),
                    ),
                )
                await s.commit()

        # Post two ₱600 payments concurrently against ₱1000 loan
        results = await asyncio.gather(
            post_one("600.00"),
            post_one("600.00"),
            return_exceptions=True,
        )

        for r in results:
            assert not isinstance(r, Exception), f"Concurrent payment failed with {r}"

        async with SessionMaker() as s:
            res = await s.execute(select(Payment).where(Payment.loan_id == loan_id))
            payments = list(res.scalars().all())
            assert len(payments) == 2

            refreshed_loan = await s.get(Loan, loan_id)
            assert refreshed_loan is not None
            assert refreshed_loan.outstanding_principal == Decimal("0.00")
            assert refreshed_loan.status == "paid"
    finally:
        from sqlalchemy import delete

        async with SessionMaker() as clean_s:
            await clean_s.execute(delete(Payment).where(Payment.loan_id == loan_id))
            await clean_s.execute(delete(Loan).where(Loan.id == loan_id))
            await clean_s.execute(delete(LoanRequest).where(LoanRequest.id == request_id))
            await clean_s.execute(delete(Borrower).where(Borrower.id == borrower_id))
            await clean_s.commit()
