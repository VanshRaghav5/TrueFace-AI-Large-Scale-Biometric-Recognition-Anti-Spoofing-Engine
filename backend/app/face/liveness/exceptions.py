"""Exceptions for the face presentation-attack detection component."""


class PadError(RuntimeError):
    """Base class for PAD failures."""


class PadInputError(PadError):
    """Raised when PAD input is invalid or unsupported."""


class PadModelUnavailableError(PadError):
    """Raised when PAD weights are not configured or cannot be loaded."""


class PadInferenceError(PadError):
    """Raised when PAD inference or output validation fails."""


class PadOutputContractError(PadInferenceError):
    """Raised when a model output does not match its documented contract."""
