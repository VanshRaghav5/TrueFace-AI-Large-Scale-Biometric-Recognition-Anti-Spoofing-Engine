"""
Custom exceptions for the face recognition module.

These exceptions provide structured error handling for the face recognition
pipeline, enabling clear error reporting and appropriate HTTP status mapping
in the API layer.
"""


class FaceRecognitionError(Exception):
    """Base exception for all face recognition errors."""

    def __init__(self, message: str = "Face recognition error occurred"):
        self.message = message
        super().__init__(self.message)


class FaceNotDetectedError(FaceRecognitionError):
    """Raised when no face is detected in the provided image."""

    def __init__(self, message: str = "No face detected in the provided image"):
        super().__init__(message)


class MultipleFacesDetectedError(FaceRecognitionError):
    """Raised when multiple faces are detected where exactly one is expected."""

    def __init__(self, face_count: int = 0, message: str = ""):
        if not message:
            message = (
                f"Multiple faces detected ({face_count}). "
                "Exactly one face is required for recognition."
            )
        self.face_count = face_count
        super().__init__(message)


class InvalidImageError(FaceRecognitionError):
    """Raised when the provided image is invalid, corrupt, or unreadable."""

    def __init__(self, message: str = "Invalid or unreadable image provided"):
        super().__init__(message)


class ModelUnavailableError(FaceRecognitionError):
    """Raised when the recognition model cannot be loaded or is not available."""

    def __init__(self, message: str = "Face recognition model is unavailable"):
        super().__init__(message)

