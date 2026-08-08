"""Pydantic schemas for Double-Entry Accounting."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccountResponse(BaseModel):
    """Public read model for an account in the Chart of Accounts."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    account_type: str
    normal_balance: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class JournalEntryResponse(BaseModel):
    """Public read model for a journal entry line."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    journal_transaction_id: UUID
    account_id: UUID
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal


class JournalTransactionResponse(BaseModel):
    """Public read model for a journal transaction header and lines."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    source_id: UUID
    description: str
    effective_date: date
    posted_at: datetime
    reversal_of_id: UUID | None
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    entries: list[JournalEntryResponse]


class JournalReversalRequest(BaseModel):
    """Request payload for reversing a journal transaction."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)
