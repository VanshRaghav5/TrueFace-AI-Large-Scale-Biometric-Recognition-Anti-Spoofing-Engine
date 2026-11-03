from pydantic import BaseModel, Field
from typing import Optional, List
from .face import ModalityStatus

class AudioQualityMetrics(BaseModel):
    duration_seconds: float = Field(..., ge=0.0)
    speech_ratio: float = Field(..., ge=0.0, le=1.0, description="Fraction of audio containing detected speech")
    snr_db: Optional[float] = Field(None, description="Estimated Signal-to-Noise Ratio in dB")

class VoiceResult(BaseModel):
    status: ModalityStatus = ModalityStatus.AVAILABLE
    speech_detected: bool = True
    identity_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    antispoof_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Genuine speech probability (1.0 = live)")
    quality: Optional[AudioQualityMetrics] = None
    reason_codes: List[str] = Field(default_factory=list)

