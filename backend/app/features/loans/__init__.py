"""Loan domain feature module."""

from app.features.loans.models import LOAN_STATUSES, PAYMENT_FREQUENCIES, Loan

__all__ = ["Loan", "LOAN_STATUSES", "PAYMENT_FREQUENCIES"]
