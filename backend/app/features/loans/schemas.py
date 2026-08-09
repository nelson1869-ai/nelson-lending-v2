"""Pydantic schemas for loan quote API request and response data."""

import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.features.loans.calculator import LoanQuote, ScheduleItem


class LoanSchema(BaseModel):
    """Base schema using mobile-friendly camelCase JSON aliases."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )


class LoanQuoteRequest(LoanSchema):
    """Stateless loan quote calculation request."""

    principal: Decimal = Field(..., gt=0, description="Original loan principal in PHP")
    monthly_rate: Decimal = Field(..., ge=0, description="Contractual monthly interest rate")
    term_months: int = Field(..., gt=0, description="Loan term in months")
    payment_frequency: Literal["monthly", "twice_monthly"] = Field(
        ..., description="Payment frequency"
    )
    first_due_date: date = Field(..., description="Date of first scheduled payment")

    @model_validator(mode="after")
    def validate_twice_monthly_first_due_date(self) -> "LoanQuoteRequest":
        if self.payment_frequency == "twice_monthly":
            last_day = calendar.monthrange(self.first_due_date.year, self.first_due_date.month)[1]
            if self.first_due_date.day != 15 and self.first_due_date.day != last_day:
                raise ValueError(
                    "Twice a Month first due date must be either the 15th "
                    "or the last calendar day of the month"
                )
        return self


class ScheduleItemResponse(LoanSchema):
    """Single installment item in calculated schedule."""

    installment_number: int
    due_date: date
    opening_principal: Decimal
    interest_due: Decimal
    scheduled_principal: Decimal
    scheduled_payment: Decimal
    closing_principal: Decimal

    @classmethod
    def from_domain(cls, item: ScheduleItem) -> "ScheduleItemResponse":
        return cls(
            installment_number=item.installment_number,
            due_date=item.due_date,
            opening_principal=item.opening_principal,
            interest_due=item.interest_due,
            scheduled_principal=item.scheduled_principal,
            scheduled_payment=item.scheduled_payment,
            closing_principal=item.closing_principal,
        )


class LoanQuoteResponse(LoanSchema):
    """Stateless loan quote calculation response."""

    principal: Decimal
    monthly_rate: Decimal
    term_months: int
    payment_frequency: str
    number_of_payments: int
    period_rate: Decimal
    scheduled_payment: Decimal
    total_scheduled_interest: Decimal
    total_scheduled_repayment: Decimal
    first_due_date: date
    final_due_date: date
    schedule: list[ScheduleItemResponse]

    @classmethod
    def from_domain(cls, quote: LoanQuote) -> "LoanQuoteResponse":
        return cls(
            principal=quote.principal,
            monthly_rate=quote.monthly_rate,
            term_months=quote.term_months,
            payment_frequency=quote.payment_frequency,
            number_of_payments=quote.number_of_payments,
            period_rate=quote.period_rate,
            scheduled_payment=quote.scheduled_payment,
            total_scheduled_interest=quote.total_scheduled_interest,
            total_scheduled_repayment=quote.total_scheduled_repayment,
            first_due_date=quote.first_due_date,
            final_due_date=quote.final_due_date,
            schedule=[ScheduleItemResponse.from_domain(item) for item in quote.schedule],
        )


class BorrowerSummarySchema(LoanSchema):
    """Minimal borrower summary for owner loan views."""

    id: UUID
    first_name: str
    last_name: str
    phone_number_normalized: str


class OwnerLoanResponse(LoanSchema):
    """Owner view of a loan contract."""

    id: UUID
    loan_request_id: UUID | None
    borrower_id: UUID
    borrower: BorrowerSummarySchema | None = None
    original_principal: Decimal
    outstanding_principal: Decimal
    accrued_interest: Decimal = Decimal("0.00")
    monthly_rate: Decimal
    term_months: int
    payment_frequency: str
    number_of_payments: int
    first_due_date: date
    final_due_date: date
    next_interest_due_date: date | None = None
    status: str
    disbursed_at: datetime | None = None
    cancelled_at: datetime | None = None
    paid_at: datetime | None = None
    defaulted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OwnerLoanDetailResponse(OwnerLoanResponse):
    """Owner detail view of a loan contract with schedule preview."""

    quote_preview: LoanQuoteResponse | None = None


class BorrowerLoanResponse(LoanSchema):
    """Borrower view of a loan contract (omitting owner metadata)."""

    id: UUID
    loan_request_id: UUID | None
    original_principal: Decimal
    outstanding_principal: Decimal
    accrued_interest: Decimal = Decimal("0.00")
    monthly_rate: Decimal
    term_months: int
    payment_frequency: str
    number_of_payments: int
    first_due_date: date
    final_due_date: date
    next_interest_due_date: date | None = None
    next_payment_amount: Decimal | None = None
    next_interest_amount: Decimal | None = None
    next_principal_amount: Decimal | None = None
    status: str
    disbursed_at: datetime | None = None
    cancelled_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime


class BorrowerLoanDetailResponse(BorrowerLoanResponse):
    """Borrower detail view of a loan contract with schedule preview."""

    quote_preview: LoanQuoteResponse | None = None
