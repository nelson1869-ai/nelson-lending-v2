"""Borrower activation and authentication domain failures."""


class BorrowerAuthFailed(Exception):
    """Generic public authentication or activation failure."""


class ActivationUnavailable(Exception):
    """Owner cannot issue a code for the requested account state."""


class BorrowerNotFound(Exception):
    """Requested business Borrower does not exist."""
