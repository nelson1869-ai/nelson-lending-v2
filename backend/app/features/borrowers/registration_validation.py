"""Canonical normalization for sensitive Borrower registration identity fields."""

import re

_PH_MOBILE_PATTERN = re.compile(r"^(?:\+639|639|09)(\d{9})$")


def normalize_philippine_mobile(value: str) -> str:
    """Normalize supported Philippine mobile forms to +639XXXXXXXXX."""

    compact = re.sub(r"[\s-]", "", value.strip())
    match = _PH_MOBILE_PATTERN.fullmatch(compact)
    if match is None:
        raise ValueError("Phone number must be a valid Philippine mobile number")
    return f"+639{match.group(1)}"


def normalize_national_id(value: str) -> str:
    """Trim and uppercase a generic national identifier without inventing an ID format."""

    normalized = value.strip().upper()
    if not 3 <= len(normalized) <= 100:
        raise ValueError("National ID must contain between 3 and 100 characters")
    return normalized
