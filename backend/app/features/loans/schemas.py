"""Pydantic schemas for loan quote API request and response data."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.features.loans.calculator import LoanQuote, ScheduleItem


class LoanQuoteRequest(BaseModel):
    """Stateless loan quote calculation request."""

    model_config = ConfigDict(populate_by_name=True)

    principal: Decimal = Field(..., gt=0, description="Original loan principal in PHP")
    monthly_rate: Decimal = Field(
        ..., ge=0, alias="monthlyRate", description="Contractual monthly interest rate"
    )
    term_months: int = Field(..., gt=0, alias="termMonths", description="Loan term in months")
    payment_frequency: Literal["monthly", "twice_monthly"] = Field(
        ..., alias="paymentFrequency", description="Payment frequency"
    )
    first_due_date: date = Field(
        ..., alias="firstDueDate", description="Date of first scheduled payment"
    )


class ScheduleItemResponse(BaseModel):
    """Single installment item in calculated schedule."""

    model_config = ConfigDict(populate_by_name=True)

    installment_number: int = Field(..., alias="installmentNumber")
    due_date: date = Field(..., alias="dueDate")
    opening_principal: Decimal = Field(..., alias="openingPrincipal")
    interest_due: Decimal = Field(..., alias="interestDue")
    scheduled_principal: Decimal = Field(..., alias="scheduledPrincipal")
    scheduled_payment: Decimal = Field(..., alias="scheduledPayment")
    closing_principal: Decimal = Field(..., alias="closingPrincipal")

    @classmethod
    from_domain(cls, item: ScheduleItem) -> "ScheduleItemResponse":
        return cls(
            installment_number=item.installment_number,
            due_date=item.due_date,
            opening_principal=item.opening_principal,
            interest_due=item.interest_due,
            scheduled_principal=item.scheduled_principal,
            scheduled_payment=item.scheduled_payment,
            closing_principal=item.closing_principal,
        )


class LoanQuoteResponse(BaseModel):
    """Stateless loan quote calculation response."""

    model_config = ConfigDict(populate_by_name=True)

    principal: Decimal
    monthly_rate: Decimal = Field(..., alias="monthlyRate")
    term_months: int = Field(..., alias="termMonths")
    payment_frequency: str = Field(..., alias="paymentFrequency")
    number_of_payments: int = Field(..., alias="numberOfPayments")
    period_rate: Decimal = Field(..., alias="periodRate")
    scheduled_payment: Decimal = Field(..., alias="scheduledPayment")
    total_scheduled_interest: Decimal = Field(..., alias="totalScheduledInterest")
    total_scheduled_repayment: Decimal = Field(..., alias="totalScheduledRepayment")
    first_due_date: date = Field(..., alias="firstDueDate")
    final_due_date: date = Field(..., alias="finalDueDate")
    schedule: list[ScheduleItemResponse]

    @classmethod
    from_domain(cls, quote: LoanQuote) -> "LoanQuoteResponse":
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
