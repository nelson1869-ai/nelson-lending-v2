"""Persistence model for the one business settings row."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import RATE_SQL_TYPE


class BusinessSetting(TimestampMixin, Base):
    """Singleton business configuration; financial rates require explicit Owner configuration."""

    __tablename__ = "business_settings"
    __table_args__ = (
        CheckConstraint("id = 'default'", name="business_setting_singleton"),
        CheckConstraint(
            "default_monthly_estimate_rate IS NULL OR default_monthly_estimate_rate >= 0",
            name="business_setting_nonnegative_estimate_rate",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    business_name: Mapped[str] = mapped_column(
        String(200), nullable=False, default="Lending Nelson", server_default="Lending Nelson"
    )
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False, default="PHP", server_default="PHP"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Asia/Manila", server_default="Asia/Manila"
    )
    receipt_footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_monthly_estimate_rate: Mapped[Decimal | None] = mapped_column(
        RATE_SQL_TYPE,
        nullable=True,
        default=None,
    )
