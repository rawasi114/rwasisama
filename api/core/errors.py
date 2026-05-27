"""Domain errors raised by services and the API."""


class RawasiError(Exception):
    """Base exception for all domain errors."""


class ValidationError(RawasiError):
    """Raised when domain validation fails."""


class NotFoundError(RawasiError):
    """Raised when a resource is not found."""


class NormalizationError(RawasiError):
    """Raised when item normalization cannot proceed."""


class AllocationError(RawasiError):
    """Raised when reverse price allocation fails its invariants."""


class InsufficientDataError(RawasiError):
    """Raised when an engine cannot produce a result for lack of data."""


class ClaudeExtractionError(RawasiError):
    """Raised when Claude extraction returns malformed output."""
