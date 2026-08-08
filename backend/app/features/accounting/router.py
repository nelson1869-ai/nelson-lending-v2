"""Owner API router for Double-Entry Accounting."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.features.accounting.schemas import (
    AccountResponse,
    JournalEntryResponse,
    JournalReversalRequest,
    JournalTransactionResponse,
)
from app.features.accounting.service import (
    CannotReverseReversalError,
    JournalAlreadyReversedError,
    JournalNotFoundError,
    UnbalancedJournalError,
    get_journal_detail,
    list_accounts,
    list_journals,
    reverse_journal,
)
from app.features.owner_identity.dependencies import get_current_owner
from app.features.owner_identity.models import OwnerUser

CurrentOwner = Annotated[OwnerUser, Depends(get_current_owner)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]

owner_router = APIRouter(prefix="/owner/accounting", tags=["Accounting"])


def _map_journal_response(tx) -> JournalTransactionResponse:
    entry_responses = [
        JournalEntryResponse(
            id=e.id,
            journal_transaction_id=e.journal_transaction_id,
            account_id=e.account_id,
            account_code=e.account.code,
            account_name=e.account.name,
            debit=e.debit,
            credit=e.credit,
        )
        for e in tx.entries
    ]
    tot_debit = (
        sum((e.debit for e in entry_responses), Decimal("0.00"))
        if entry_responses
        else Decimal("0.00")
    )
    tot_credit = (
        sum((e.credit for e in entry_responses), Decimal("0.00"))
        if entry_responses
        else Decimal("0.00")
    )
    return JournalTransactionResponse(
        id=tx.id,
        event_type=tx.event_type,
        source_id=tx.source_id,
        description=tx.description,
        effective_date=tx.effective_date,
        posted_at=tx.posted_at,
        reversal_of_id=tx.reversal_of_id,
        total_debit=tot_debit,
        total_credit=tot_credit,
        is_balanced=(tot_debit == tot_credit),
        entries=entry_responses,
    )


@owner_router.get(
    "/accounts",
    response_model=list[AccountResponse],
    summary="List Chart of Accounts",
)
async def owner_list_accounts(
    session: DatabaseSession,
    _: CurrentOwner,
) -> list[AccountResponse]:
    """Retrieve system Chart of Accounts."""
    accounts = await list_accounts(session)
    return [AccountResponse.model_validate(acc) for acc in accounts]


@owner_router.get(
    "/journals",
    response_model=list[JournalTransactionResponse],
    summary="List Journal Transactions",
)
async def owner_list_journals(
    session: DatabaseSession,
    _: CurrentOwner,
) -> list[JournalTransactionResponse]:
    """Retrieve all recorded double-entry accounting transactions."""
    journals = await list_journals(session)
    return [_map_journal_response(tx) for tx in journals]


@owner_router.get(
    "/journals/{journal_id}",
    response_model=JournalTransactionResponse,
    summary="Get Journal Transaction Detail",
)
async def owner_get_journal(
    journal_id: UUID,
    session: DatabaseSession,
    _: CurrentOwner,
) -> JournalTransactionResponse:
    """Retrieve a specific journal transaction and its line entries."""
    try:
        journal = await get_journal_detail(session, journal_id)
        return _map_journal_response(journal)
    except JournalNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@owner_router.post(
    "/journals/{journal_id}/reverse",
    response_model=JournalTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reverse a Journal Transaction",
)
async def owner_reverse_journal(
    journal_id: UUID,
    session: DatabaseSession,
    _: CurrentOwner,
    payload: JournalReversalRequest | None = None,
) -> JournalTransactionResponse:
    """Create a compensating reversal journal for an existing transaction."""
    req_payload = payload or JournalReversalRequest()
    try:
        reversal_tx = await reverse_journal(
            session,
            journal_id,
            reason=req_payload.reason or "",
        )
        return _map_journal_response(reversal_tx)
    except JournalNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (CannotReverseReversalError, JournalAlreadyReversedError, UnbalancedJournalError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
