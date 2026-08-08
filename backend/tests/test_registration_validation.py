"""Contract tests for Borrower registration normalization and validation."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.features.borrowers.registration_schemas import BorrowerRegistrationCreate
from app.features.borrowers.registration_validation import (
    normalize_national_id,
    normalize_philippine_mobile,
)


@pytest.mark.parametrize(
    "value",
    ["09171234567", "639171234567", "+639171234567", "0917 123 4567", "0917-123-4567"],
)
def test_philippine_mobile_normalizes_supported_forms(value: str) -> None:
    assert normalize_philippine_mobile(value) == "+639171234567"


@pytest.mark.parametrize("value", ["", "123", "08171234567", "+63917123456", "+12025550123"])
def test_philippine_mobile_rejects_malformed_numbers(value: str) -> None:
    with pytest.raises(ValueError, match="Philippine mobile"):
        normalize_philippine_mobile(value)


def test_national_id_is_trimmed_and_uppercased() -> None:
    assert normalize_national_id("  id-123abc  ") == "ID-123ABC"


def valid_payload(**overrides: object) -> BorrowerRegistrationCreate:
    values: dict[str, object] = {
        "firstName": "Juan",
        "lastName": "Dela Cruz",
        "nationalId": "ID-123456",
        "phoneNumber": "09171234567",
        "address": "Bacolod City",
        "dateOfBirth": "1995-05-10",
    }
    values.update(overrides)
    return BorrowerRegistrationCreate.model_validate(values)


def test_registration_text_is_trimmed_without_silent_truncation() -> None:
    payload = valid_payload(firstName="  Juan  ", address="  Bacolod City  ")

    assert payload.first_name == "Juan"
    assert payload.address == "Bacolod City"


@pytest.mark.parametrize("field", ["firstName", "lastName", "nationalId", "address"])
def test_registration_rejects_blank_critical_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        valid_payload(**{field: "   "})


@pytest.mark.parametrize("dob", [date.today(), date.today() + timedelta(days=1)])
def test_registration_rejects_nonpast_date_of_birth(dob: date) -> None:
    with pytest.raises(ValidationError, match="must be in the past"):
        valid_payload(dateOfBirth=dob)
