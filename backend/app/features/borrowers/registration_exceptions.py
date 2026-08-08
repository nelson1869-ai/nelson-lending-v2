"""Stable registration workflow exceptions."""


class RegistrationConflict(Exception):
    """Raised when supplied identity already has a registration or account."""


class RegistrationNotFound(Exception):
    """Raised when a registration does not exist."""


class RegistrationStateConflict(Exception):
    """Raised when a terminal registration is reviewed again."""
