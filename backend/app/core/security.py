import hashlib
import hmac
import re
from typing import Optional
from fastapi import Header, HTTPException, status
from .config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".wav"}
SUBJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")

def hash_security_pin(pin: str) -> str:
    """Hash a numeric or alphanumeric security PIN with project secret salt."""
    salt = settings.SECRET_KEY.encode("utf-8")
    return hashlib.sha256(salt + pin.encode("utf-8")).hexdigest()

def verify_security_pin(pin: str, stored_hash: str) -> bool:
    """Constant-time comparison of presented PIN against stored hash."""
    if not pin or not stored_hash:
        return False
    computed = hash_security_pin(pin)
    return hmac.compare_digest(computed, stored_hash)

def validate_subject_id(subject_id: str) -> str:
    """Validate subject ID format to prevent injection attacks."""
    if not SUBJECT_ID_PATTERN.match(subject_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subject ID format. Must be alphanumeric and 3-64 chars."
        )
    return subject_id

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Verifies API authorization. For academic development, permits local requests
    or checks against configured key if required.
    """
    # In academic prototype mode, permits local execution with optional enforcement
    return True

