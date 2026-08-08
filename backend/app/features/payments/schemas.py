"""Payment schemas for request validation and response serialization."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentPostRequest(BaseModel):
    """Payload submitted by Owner to record a received payment."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        description="Payment amount in PHP, must be greater than zero",
    )
    payment_date: date = Field(
        ...,
        description="Effective business date of payment",
    )
    reference: str | None = Field(
        default=None,
        max_length=100,
        description="Optional payment reference (e.g. receipt number, bank ref, GCash ref)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Optional internal note recorded by Owner",
    )
    idempotency_key: str | None = Field(
        default=None,
        max_length=128,
        description=(
            "Client-generated idempotency key. Retrying with the same key and identical "
            "payload returns the original payment. Retrying with the same key but a "
            "conflicting amount or date is rejected with HTTP 409."
        ),
    )


class PaymentResponse(BaseModel):
    """Full payment record visible to Owner."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    loan_id: UUID
    amount: Decimal
    interest_paid: Decimal
    principal_paid: Decimal
    unapplied_credit: Decimal
    remaining_interest: Decimal
    remaining_principal: Decimal
    payment_date: date
    posted_at: datetime
    reference: str | None = None
    note: str | None = None
    idempotency_key: str | None = None
    created_at: datetime


class BorrowerPaymentResponse(BaseModel):
    """Borrower-safe payment record (omits internal Owner note)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    loan_id: UUID
    amount: Decimal
    interest_paid: Decimal
    principal_paid: Decimal
    unapplied_credit: Decimal
    remaining_interest: Decimal
    remaining_principal: Decimal
    payment_date: date
    posted_at: datetime
    reference: str | None = None
    idempotency_key: str | None = None
