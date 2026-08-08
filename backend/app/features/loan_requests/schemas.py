"""Pydantic schemas for loan requests API request and response payloads."""

import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.features.loans.schemas import LoanQuoteResponse


class LoanRequestBaseSchema(BaseModel):
    """Base schema using mobile-friendly camelCase JSON aliases."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class BorrowerLoanQuoteRequest(LoanRequestBaseSchema):
    """Borrower payload when requesting a stateless loan quote preview."""

    principal: Decimal = Field(..., gt=0, description="Requested principal in PHP")
    term_months: int = Field(..., gt=0, description="Loan term in months")
    payment_frequency: Literal["monthly", "twice_monthly"] = Field(
        ..., description="Payment frequency"
    )
    first_due_date: date = Field(..., description="Date of first scheduled payment")

    @model_validator(mode="after")
    def validate_twice_monthly_first_due_date(self) -> "BorrowerLoanQuoteRequest":
        if self.payment_frequency == "twice_monthly":
            last_day = calendar.monthrange(self.first_due_date.year, self.first_due_date.month)[1]
            if self.first_due_date.day != 15 and self.first_due_date.day != last_day:
                raise ValueError(
                    "Twice a Month first due date must be either the 15th "
                    "or the last calendar day of the month"
                )
        return self


class BorrowerLoanRequestCreate(LoanRequestBaseSchema):
    """Borrower payload when submitting a loan request."""

    principal: Decimal = Field(..., gt=0, description="Requested principal in PHP")
    term_months: int = Field(..., gt=0, description="Loan term in months")
    payment_frequency: Literal["monthly", "twice_monthly"] = Field(
        ..., description="Payment frequency"
    )
    first_due_date: date = Field(..., description="Date of first scheduled payment")

    @model_validator(mode="after")
    def validate_twice_monthly_first_due_date(self) -> "BorrowerLoanRequestCreate":
        if self.payment_frequency == "twice_monthly":
            last_day = calendar.monthrange(self.first_due_date.year, self.first_due_date.month)[1]
            if self.first_due_date.day != 15 and self.first_due_date.day != last_day:
                raise ValueError(
                    "Twice a Month first due date must be either the 15th "
                    "or the last calendar day of the month"
                )
        return self


LoanRequestCreate = BorrowerLoanRequestCreate


class BorrowerLoanRequestResponse(LoanRequestBaseSchema):
    """Borrower-safe loan request data returned to borrower."""

    id: UUID
    borrower_id: UUID
    requested_principal: Decimal
    requested_monthly_rate: Decimal
    requested_term_months: int
    requested_payment_frequency: str
    requested_first_due_date: date
    status: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime


class OwnerLoanRequestResponse(LoanRequestBaseSchema):
    """Loan request data returned to owner, including internal review metadata."""

    id: UUID
    borrower_id: UUID
    requested_principal: Decimal
    requested_monthly_rate: Decimal
    requested_term_months: int
    requested_payment_frequency: str
    requested_first_due_date: date
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_owner_id: UUID | None = None
    owner_note: str | None = None
    created_at: datetime
    updated_at: datetime


class OwnerLoanRequestDetailResponse(OwnerLoanRequestResponse):
    """Detailed loan request payload for owner review including quote preview."""

    borrower_first_name: str
    borrower_last_name: str
    borrower_national_id: str
    borrower_phone_number: str
    quote_preview: LoanQuoteResponse


class LoanRequestReviewRequest(LoanRequestBaseSchema):
    """Owner review decision payload (for approve/reject actions)."""

    owner_note: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional internal review note",
    )
