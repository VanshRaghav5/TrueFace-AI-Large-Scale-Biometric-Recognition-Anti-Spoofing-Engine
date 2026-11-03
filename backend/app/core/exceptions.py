from typing import Optional

class BiometricException(Exception):
    """Base exception for all TrueFace AI-X biometric pipeline errors."""
    def __init__(self, message: str, reason_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code or "INTERNAL_PROCESSING_ERROR"

class ModalityMissingError(BiometricException):
    def __init__(self, message: str = "Required biometric modality sample is missing"):
        super().__init__(message, "MODALITY_MISSING")

class BiometricQualityError(BiometricException):
    def __init__(self, message: str, reason_code: str = "FACE_QUALITY_LOW"):
        super().__init__(message, reason_code)

class ModelTimeoutError(BiometricException):
    def __init__(self, message: str = "Model inference exceeded configured timeout"):
        super().__init__(message, "MODEL_TIMEOUT")

class ModelUnavailableError(BiometricException):
    def __init__(self, message: str = "Configured biometric model checkpoint is unavailable"):
        super().__init__(message, "MODEL_UNAVAILABLE")

class ConsentRequiredError(BiometricException):
    def __init__(self, message: str = "Explicit subject consent is required for biometric enrollment"):
        super().__init__(message, "CONSENT_REQUIRED")

