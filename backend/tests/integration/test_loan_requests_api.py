"""Integration tests for Borrower and Owner Loan Requests APIs."""

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.borrowers.auth_security import create_borrower_access_token
from app.features.borrowers.models import Borrower, BorrowerAccount
from app.features.business_settings.models import BusinessSetting
from app.features.loans.models import Loan
from app.features.owner_identity.service import bootstrap_owner, login_owner
from app.main import app

pytestmark = pytest.mark.integration

BORROWER_QUOTE_URL = "/api/v1/borrower/loan-requests/quote"
BORROWER_REQUESTS_URL = "/api/v1/borrower/loan-requests"
OWNER_REQUESTS_URL = "/api/v1/owner/loan-requests"
OWNER_LOANS_QUOTE_URL = "/api/v1/owner/loans/quote"
OWNER_PASS = "owner req test pass 123"


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


async def setup_owner_token(db_session: AsyncSession) -> dict[str, str]:
    await bootstrap_owner(db_session, username="ownerreq", password=OWNER_PASS)
    pair = await login_owner(db_session, username="ownerreq", password=OWNER_PASS)
    return {"Authorization": f"Bearer {pair.access_token.value}"}


async def setup_borrower_token(
    db_session: AsyncSession,
    suffix: str = "201",
) -> tuple[dict[str, str], Borrower]:
    b = Borrower(
        first_name="Borrower",
        last_name=f"Request {suffix}",
        national_id=f"B-REQ-ID-{suffix}",
        address="123 Test St",
        phone_number=f"0919{suffix:0>7}",
        phone_number_normalized=f"+63919{suffix:0>7}",
        date_of_birth=date(1992, 4, 10),
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


async def set_business_estimate_rate(
    db_session: AsyncSession,
    rate: Decimal | str | None,
) -> None:
    val = Decimal(str(rate)) if rate is not None else None
    await db_session.execute(
        update(BusinessSetting)
        .where(BusinessSetting.id == "default")
        .values(default_monthly_estimate_rate=val)
    )
    await db_session.flush()


async def test_borrower_quote_preview(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.05")
    headers, _ = await setup_borrower_token(db_session, "301")
    res = await api_client.post(
        BORROWER_QUOTE_URL,
        headers=headers,
        json={
            "principal": "5000.00",
            "termMonths": 2,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["principal"] == "5000.00"
    assert data["monthlyRate"] == "0.0500000000"
    assert data["numberOfPayments"] == 2


async def test_borrower_submit_loan_request(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.06")
    headers, _ = await setup_borrower_token(db_session, "302")
    res = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers,
        json={
            "principal": "4000.00",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "pending"
    assert data["requestedPrincipal"] == "4000.00"
    assert data["requestedMonthlyRate"] == "0.0600000000"
    assert "ownerNote" not in data
    assert "reviewedByOwnerId" not in data


async def test_borrower_submit_invalid_twice_monthly_date(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.05")
    headers, _ = await setup_borrower_token(db_session, "303")
    res = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers,
        json={
            "principal": "4000.00",
            "termMonths": 3,
            "paymentFrequency": "twice_monthly",
            "firstDueDate": "2026-09-07",
        },
    )
    assert res.status_code == 422


async def test_borrower_duplicate_pending_request_conflict(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.05")
    headers, _ = await setup_borrower_token(db_session, "304")
    res1 = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers,
        json={
            "principal": "2000.00",
            "termMonths": 1,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res1.status_code == 201

    res2 = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers,
        json={
            "principal": "3000.00",
            "termMonths": 2,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res2.status_code == 409


async def test_borrower_cross_borrower_isolation(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.05")
    headers_b1, _ = await setup_borrower_token(db_session, "305")
    headers_b2, _ = await setup_borrower_token(db_session, "306")

    res = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers_b1,
        json={
            "principal": "1000.00",
            "termMonths": 1,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    req_id = res.json()["id"]

    res_isolation = await api_client.get(
        f"{BORROWER_REQUESTS_URL}/{req_id}",
        headers=headers_b2,
    )
    assert res_isolation.status_code == 404


async def test_borrower_cancel_pending_request(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.05")
    headers, _ = await setup_borrower_token(db_session, "307")
    res_sub = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers,
        json={
            "principal": "2000.00",
            "termMonths": 1,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    req_id = res_sub.json()["id"]

    res_cancel = await api_client.post(
        f"{BORROWER_REQUESTS_URL}/{req_id}/cancel",
        headers=headers,
    )
    assert res_cancel.status_code == 200
    data = res_cancel.json()
    assert data["status"] == "cancelled"
    assert "ownerNote" not in data
    assert "reviewedByOwnerId" not in data

    res_again = await api_client.post(
        f"{BORROWER_REQUESTS_URL}/{req_id}/cancel",
        headers=headers,
    )
    assert res_again.status_code == 409


async def test_owner_review_approve_and_reject(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    await set_business_estimate_rate(db_session, "0.05")
    headers_b1, _ = await setup_borrower_token(db_session, "308")
    headers_b2, _ = await setup_borrower_token(db_session, "309")

    res_b1 = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers_b1,
        json={
            "principal": "3000.00",
            "termMonths": 2,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    req1_id = res_b1.json()["id"]

    res_b2 = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers_b2,
        json={
            "principal": "4000.00",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    req2_id = res_b2.json()["id"]

    res_list = await api_client.get(OWNER_REQUESTS_URL, headers=owner_headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) >= 2

    res_detail = await api_client.get(
        f"{OWNER_REQUESTS_URL}/{req1_id}",
        headers=owner_headers,
    )
    assert res_detail.status_code == 200
    assert res_detail.json()["quotePreview"]["principal"] == "3000.00"

    loan_count_before = (await db_session.execute(select(func.count()).select_from(Loan))).scalar()

    res_app = await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req1_id}/approve",
        headers=owner_headers,
        json={"ownerNote": "Approved after document check"},
    )
    assert res_app.status_code == 200
    app_data = res_app.json()
    assert app_data["status"] == "approved"
    assert app_data["ownerNote"] == "Approved after document check"
    assert "reviewedByOwnerId" in app_data

    loan_count_after = (await db_session.execute(select(func.count()).select_from(Loan))).scalar()
    assert loan_count_before == loan_count_after

    res_rej = await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req2_id}/reject",
        headers=owner_headers,
        json={"ownerNote": "Income requirement not met"},
    )
    assert res_rej.status_code == 200
    rej_data = res_rej.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["ownerNote"] == "Income requirement not met"

    res_re_app = await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req1_id}/approve",
        headers=owner_headers,
    )
    assert res_re_app.status_code == 409


async def test_token_role_isolation(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    borrower_headers, _ = await setup_borrower_token(db_session, "310")

    # Borrower token on Owner endpoint -> 401
    res_b_on_o = await api_client.get(OWNER_REQUESTS_URL, headers=borrower_headers)
    assert res_b_on_o.status_code == 401

    # Owner token on Borrower endpoint -> 401
    res_o_on_b = await api_client.get(BORROWER_REQUESTS_URL, headers=owner_headers)
    assert res_o_on_b.status_code == 401


async def test_owner_review_concurrency_lock(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    await set_business_estimate_rate(db_session, "0.05")
    headers_b, _ = await setup_borrower_token(db_session, "311")

    res_sub = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=headers_b,
        json={
            "principal": "5000.00",
            "termMonths": 2,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    req_id = res_sub.json()["id"]

    # First review succeeds
    res_app = await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req_id}/approve",
        headers=owner_headers,
    )
    assert res_app.status_code == 200

    # Second concurrent review attempt on same request fails with 409 Conflict
    res_rej = await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req_id}/reject",
        headers=owner_headers,
    )
    assert res_rej.status_code == 409


# Finding 1 Privacy Tests
async def test_borrower_privacy_responses_omit_owner_metadata(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    await set_business_estimate_rate(db_session, "0.05")
    borrower_headers, _ = await setup_borrower_token(db_session, "312")

    # 1. Submit response privacy check
    res_sub = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=borrower_headers,
        json={
            "principal": "5000.00",
            "termMonths": 2,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res_sub.status_code == 201
    sub_data = res_sub.json()
    assert "ownerNote" not in sub_data
    assert "reviewedByOwnerId" not in sub_data

    req_id = sub_data["id"]

    # Owner approves with note
    await api_client.post(
        f"{OWNER_REQUESTS_URL}/{req_id}/approve",
        headers=owner_headers,
        json={"ownerNote": "Confidential internal owner rating: Grade A"},
    )

    # 2. List response privacy check
    res_list = await api_client.get(BORROWER_REQUESTS_URL, headers=borrower_headers)
    assert res_list.status_code == 200
    list_item = res_list.json()[0]
    assert "ownerNote" not in list_item
    assert "reviewedByOwnerId" not in list_item

    # 3. Detail response privacy check
    res_detail = await api_client.get(
        f"{BORROWER_REQUESTS_URL}/{req_id}",
        headers=borrower_headers,
    )
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "ownerNote" not in detail_data
    assert "reviewedByOwnerId" not in detail_data


# Finding 2 Server Rate Control Tests
async def test_borrower_quote_uses_configured_business_estimate_rate(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, "0.035")
    borrower_headers, _ = await setup_borrower_token(db_session, "313")

    res = await api_client.post(
        BORROWER_QUOTE_URL,
        headers=borrower_headers,
        json={
            "principal": "10000.00",
            "termMonths": 6,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res.status_code == 200
    assert res.json()["monthlyRate"] == "0.0350000000"


async def test_borrower_submit_uses_configured_rate_and_persists_snapshot(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    await set_business_estimate_rate(db_session, "0.045")
    borrower_headers, _ = await setup_borrower_token(db_session, "314")

    res = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=borrower_headers,
        json={
            "principal": "8000.00",
            "termMonths": 4,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res.status_code == 201
    req_id = res.json()["id"]
    assert res.json()["requestedMonthlyRate"] == "0.0450000000"

    # Owner changes rate setting later
    await set_business_estimate_rate(db_session, "0.090")

    # Fetching submitted request details still shows the snapshotted request rate
    res_b_detail = await api_client.get(
        f"{BORROWER_REQUESTS_URL}/{req_id}", headers=borrower_headers
    )
    assert res_b_detail.json()["requestedMonthlyRate"] == "0.0450000000"

    res_o_detail = await api_client.get(f"{OWNER_REQUESTS_URL}/{req_id}", headers=owner_headers)
    assert res_o_detail.json()["requestedMonthlyRate"] == "0.0450000000"
    assert res_o_detail.json()["quotePreview"]["monthlyRate"] == "0.0450000000"


async def test_missing_business_estimate_rate_fails_safely(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await set_business_estimate_rate(db_session, None)
    borrower_headers, _ = await setup_borrower_token(db_session, "315")

    res_quote = await api_client.post(
        BORROWER_QUOTE_URL,
        headers=borrower_headers,
        json={
            "principal": "5000.00",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res_quote.status_code == 400
    assert "not yet been configured" in res_quote.json()["detail"]

    res_submit = await api_client.post(
        BORROWER_REQUESTS_URL,
        headers=borrower_headers,
        json={
            "principal": "5000.00",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res_submit.status_code == 400
    assert "not yet been configured" in res_submit.json()["detail"]


async def test_owner_m09_quote_endpoint_unaffected(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_headers = await setup_owner_token(db_session)
    res = await api_client.post(
        OWNER_LOANS_QUOTE_URL,
        headers=owner_headers,
        json={
            "principal": "5000.00",
            "monthlyRate": "0.075",
            "termMonths": 3,
            "paymentFrequency": "monthly",
            "firstDueDate": "2026-10-01",
        },
    )
    assert res.status_code == 200
    assert res.json()["monthlyRate"] == "0.0750000000"
