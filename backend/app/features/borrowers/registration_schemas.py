"""Public and Owner-facing Borrower registration API contracts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.features.borrowers.registration_validation import (
    normalize_national_id,
    normalize_philippine_mobile,
)


class RegistrationSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class BorrowerRegistrationCreate(RegistrationSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    national_id: str = Field(min_length=3, max_length=100)
    phone_number: str = Field(min_length=1, max_length=32)
    address: str = Field(min_length=1, max_length=1000)
    date_of_birth: date

    @field_validator("first_name", "last_name", "address")
    @classmethod
    def strip_nonblank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be blank")
        return normalized

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, value: str) -> str:
        return normalize_national_id(value)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalize_philippine_mobile(value)
        return value.strip()

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")
        return value


class BorrowerRegistrationResponse(RegistrationSchema):
    registration_id: UUID
    status: str
    submitted_at: datetime
    message: str
