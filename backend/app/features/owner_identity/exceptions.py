"""Stable internal exceptions for the Owner authentication boundary."""


class AuthenticationFailed(Exception):
    """Raised for externally indistinguishable authentication failures."""


class OwnerAlreadyBootstrapped(Exception):
    """Raised when the one-time Owner bootstrap has already been consumed."""
