"""Canonical Decimal-backed SQL types for future financial models."""

from decimal import Decimal

from sqlalchemy import Numeric

MONEY_PRECISION = 18
MONEY_SCALE = 2
RATE_PRECISION = 12
RATE_SCALE = 10

type Money = Decimal
type Rate = Decimal

MONEY_SQL_TYPE: Numeric[Decimal] = Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True)
RATE_SQL_TYPE: Numeric[Decimal] = Numeric(RATE_PRECISION, RATE_SCALE, asdecimal=True)
