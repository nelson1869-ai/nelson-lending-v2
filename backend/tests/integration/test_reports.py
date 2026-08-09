"""M15 Owner dashboard aggregation, boundary, and authorization tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_owner_access_token, hash_password
from app.features.accounting.constants import (
    ACCOUNT_CASH_CODE,
    ACCOUNT_CUSTOMER_CREDIT_CODE,
    ACCOUNT_INTEREST_INCOME_CODE,
    ACCOUNT_LOANS_RECEIVABLE_CODE,
)
from app.features.accounting.service import ensure_system_accounts, post_journal
from app.features.borrowers.auth_security import create_borrower_access_token, hash_pin
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.loan_requests.models import LoanRequest
from app.features.loans.models import Loan
from app.features.owner_identity.models import OwnerUser
from app.features.payments.models import Payment
from app.features.reports.service import get_accounting_balances, get_owner_dashboard

pytestmark = pytest.mark.integration


async def _owner_headers(db: AsyncSession) -> dict[str, str]:
    owner = OwnerUser(
        username=f"reports_{uuid4().hex[:8]}",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
    )
    db.add(owner)
    await db.flush()
    token = create_owner_access_token(owner.id)
    return {"Authorization": f"Bearer {token.value}"}


async def _borrower(db: AsyncSession) -> Borrower:
    suffix = uuid4().hex[:8]
    borrower = Borrower(
        first_name="Report",
        last_name="Fixture",
        national_id=f"REPORT-{suffix}",
        address="Reporting Street",
        phone_number=f"0917{suffix[:7]}",
        phone_number_normalized=f"+63917{suffix[:7]}",
        date_of_birth=date(1990, 1, 1),
        status="active",
    )
    db.add(borrower)
    await db.flush()
    return borrower


async def _loan(db: AsyncSession, borrower: Borrower, *, status: str, principal: str) -> Loan:
    request = LoanRequest(
        borrower_id=borrower.id,
        requested_principal=Decimal(principal),
        requested_monthly_rate=Decimal("0.10"),
        requested_term_months=2,
        requested_payment_frequency="monthly",
        requested_first_due_date=date(2026, 7, 15),
        status="approved",
        submitted_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    db.add(request)
    await db.flush()
    loan = Loan(
        loan_request_id=request.id,
        borrower_id=borrower.id,
        original_principal=Decimal(principal),
        outstanding_principal=(Decimal("600.00") if status == "active" else Decimal("0.00")),
        accrued_interest=(Decimal("25.50") if status == "active" else Decimal("0.00")),
        monthly_rate=Decimal("0.10"),
        term_months=2,
        payment_frequency="monthly",
        number_of_payments=2,
        first_due_date=date(2026, 7, 15),
        final_due_date=date(2026, 8, 15),
        next_interest_due_date=date(2026, 7, 15),
        status=status,
    )
    db.add(loan)
    await db.flush()
    return loan


async def test_empty_dashboard_returns_all_canonical_statuses_and_zero_money(
    db_session: AsyncSession,
) -> None:
    dashboard = await get_owner_dashboard(
        db_session, from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)
    )

    assert [item.status for item in dashboard.portfolio.status_counts] == [
        "pending_disbursement",
        "active",
        "paid",
        "cancelled",
        "defaulted",
    ]
    assert all(item.count == 0 for item in dashboard.portfolio.status_counts)
    assert dashboard.portfolio.total_original_principal == Decimal("0.00")
    assert [item.status for item in dashboard.loan_requests.status_counts] == [
        "pending",
        "approved",
        "rejected",
        "cancelled",
    ]
    assert dashboard.collections.total_payment_amount == Decimal("0.00")
    assert [account.code for account in dashboard.accounting_balances] == [
        "1000",
        "1100",
        "2000",
        "4000",
    ]


async def test_dashboard_aggregates_portfolio_collections_and_normal_balances_exactly(
    db_session: AsyncSession,
) -> None:
    borrower = await _borrower(db_session)
    active = await _loan(db_session, borrower, status="active", principal="1000.00")
    await _loan(db_session, borrower, status="paid", principal="500.00")
    await _loan(db_session, borrower, status="cancelled", principal="9000.00")
    await _loan(db_session, borrower, status="defaulted", principal="700.00")

    db_session.add_all(
        [
            Payment(
                loan_id=active.id,
                amount=Decimal("700.00"),
                interest_paid=Decimal("100.00"),
                principal_paid=Decimal("500.00"),
                unapplied_credit=Decimal("100.00"),
                remaining_interest=Decimal("0.00"),
                remaining_principal=Decimal("500.00"),
                payment_date=date(2026, 8, 1),
                posted_at=datetime(2026, 8, 2, tzinfo=UTC),
            ),
            Payment(
                loan_id=active.id,
                amount=Decimal("300.00"),
                interest_paid=Decimal("25.00"),
                principal_paid=Decimal("275.00"),
                unapplied_credit=Decimal("0.00"),
                remaining_interest=Decimal("0.00"),
                remaining_principal=Decimal("225.00"),
                payment_date=date(2026, 8, 31),
                posted_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
            Payment(
                loan_id=active.id,
                amount=Decimal("50.00"),
                interest_paid=Decimal("0.00"),
                principal_paid=Decimal("50.00"),
                unapplied_credit=Decimal("0.00"),
                remaining_interest=Decimal("0.00"),
                remaining_principal=Decimal("175.00"),
                payment_date=date(2026, 9, 1),
                posted_at=datetime(2026, 8, 31, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    accounts = await ensure_system_accounts(db_session)
    balances_before = {
        item.code: item.balance for item in await get_accounting_balances(db_session)
    }
    await post_journal(
        db_session,
        event_type="reversal",
        source_id=uuid4(),
        description="Reporting balance fixture",
        effective_date=date(2026, 8, 1),
        entries=[
            (accounts[ACCOUNT_CASH_CODE], Decimal("1000.00"), Decimal("0.00")),
            (accounts[ACCOUNT_LOANS_RECEIVABLE_CODE], Decimal("0.00"), Decimal("775.00")),
            (accounts[ACCOUNT_INTEREST_INCOME_CODE], Decimal("0.00"), Decimal("125.00")),
            (accounts[ACCOUNT_CUSTOMER_CREDIT_CODE], Decimal("0.00"), Decimal("100.00")),
        ],
    )

    dashboard = await get_owner_dashboard(
        db_session, from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)
    )

    counts = {item.status: item.count for item in dashboard.portfolio.status_counts}
    assert counts == {
        "pending_disbursement": 0,
        "active": 1,
        "paid": 1,
        "cancelled": 1,
        "defaulted": 1,
    }
    assert dashboard.portfolio.total_original_principal == Decimal("1500.00")
    assert dashboard.portfolio.outstanding_principal == Decimal("600.00")
    assert dashboard.portfolio.accrued_interest == Decimal("25.50")
    assert dashboard.collections.total_payment_amount == Decimal("1000.00")
    assert dashboard.collections.principal_allocation == Decimal("775.00")
    assert dashboard.collections.interest_allocation == Decimal("125.00")
    assert dashboard.collections.unapplied_credit_allocation == Decimal("100.00")
    assert (
        dashboard.collections.principal_allocation
        + dashboard.collections.interest_allocation
        + dashboard.collections.unapplied_credit_allocation
        == dashboard.collections.total_payment_amount
    )
    balances = {item.code: item.balance for item in dashboard.accounting_balances}
    assert {code: balances[code] - balances_before[code] for code in balances} == {
        "1000": Decimal("1000.00"),
        "1100": Decimal("-775.00"),
        "2000": Decimal("100.00"),
        "4000": Decimal("125.00"),
    }


async def test_dashboard_api_is_owner_only_and_validates_date_range(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await _owner_headers(db_session)
    borrower = await _borrower(db_session)
    account = BorrowerAccount(
        borrower_id=borrower.id,
        phone_number=borrower.phone_number,
        phone_number_normalized=borrower.phone_number_normalized,
        account_status="activated",
        pin_hash=hash_pin("123456"),
    )
    db_session.add(account)
    await db_session.flush()
    borrower_token = create_borrower_access_token(account.id, borrower.id)
    borrower_headers = {"Authorization": f"Bearer {borrower_token.value}"}

    ok = await api_client.get(
        "/api/v1/owner/reports/dashboard?from_date=2026-08-01&to_date=2026-08-31",
        headers=owner_headers,
    )
    invalid = await api_client.get(
        "/api/v1/owner/reports/dashboard?from_date=2026-09-01&to_date=2026-08-31",
        headers=owner_headers,
    )
    unrepresentable_exclusive_end = await api_client.get(
        "/api/v1/owner/reports/dashboard?from_date=9999-12-31&to_date=9999-12-31",
        headers=owner_headers,
    )
    borrower_denied = await api_client.get(
        "/api/v1/owner/reports/dashboard?from_date=2026-08-01&to_date=2026-08-31",
        headers=borrower_headers,
    )
    anonymous_denied = await api_client.get(
        "/api/v1/owner/reports/dashboard?from_date=2026-08-01&to_date=2026-08-31"
    )

    assert ok.status_code == 200
    assert invalid.status_code == 422
    assert unrepresentable_exclusive_end.status_code == 422
    assert borrower_denied.status_code == 401
    assert anonymous_denied.status_code == 401


async def test_dashboard_route_is_present_in_openapi(api_client: AsyncClient) -> None:
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/owner/reports/dashboard" in response.json()["paths"]
