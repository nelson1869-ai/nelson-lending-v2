"""Borrower activation and authentication API contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.features.borrowers.auth_security import validate_pin
from app.features.borrowers.registration_validation import normalize_philippine_mobile


class BorrowerAuthSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ActivationCodeResponse(BorrowerAuthSchema):
    borrower_id: UUID
    expires_at: datetime
    activation_code: str


class ActivateRequest(BorrowerAuthSchema):
    phone_number: str = Field(min_length=1, max_length=32)
    activation_code: str = Field(pattern=r"^\d{6}$")
    pin: str

    @field_validator("phone_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_philippine_mobile(value)

    @field_validator("pin")
    @classmethod
    def validate_six_digit_pin(cls, value: str) -> str:
        validate_pin(value)
        return value


class ActivationResponse(BorrowerAuthSchema):
    status: Literal["activated"] = "activated"
    message: str = "Borrower account activated. Sign in to continue."


class BorrowerLoginRequest(BorrowerAuthSchema):
    phone_number: str = Field(min_length=1, max_length=32)
    pin: str
    device_identifier: str = Field(min_length=16, max_length=512)
    platform: Literal["android", "ios"]

    @field_validator("phone_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return normalize_philippine_mobile(value)

    @field_validator("pin")
    @classmethod
    def validate_six_digit_pin(cls, value: str) -> str:
        validate_pin(value)
        return value


class BorrowerTokenPairResponse(BorrowerAuthSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime


class BorrowerRefreshRequest(BorrowerAuthSchema):
    refresh_token: str = Field(min_length=1)
    device_identifier: str = Field(min_length=16, max_length=512)


class BorrowerLogoutRequest(BorrowerAuthSchema):
    refresh_token: str = Field(min_length=1)


class BorrowerMeResponse(BorrowerAuthSchema):
    borrower_id: UUID
    account_id: UUID
    first_name: str
    last_name: str
    phone_number: str
    account_status: str
