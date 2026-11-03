from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ModalityStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    INVALID = "invalid"
    LOW_QUALITY = "low_quality"
    UNSUPPORTED = "unsupported"
    TIMEOUT = "timeout"
    MODEL_UNAVAILABLE = "model_unavailable"
    ERROR = "error"

class FaceQualityMetrics(BaseModel):
    sharpness: float = Field(..., ge=0.0, description="Laplacian blur variance metric")
    illumination: float = Field(..., ge=0.0, le=1.0, description="Normalized average brightness")
    pose_yaw: Optional[float] = Field(None, description="Estimated head yaw angle")
    pose_pitch: Optional[float] = Field(None, description="Estimated head pitch angle")

class FaceResult(BaseModel):
    status: ModalityStatus = ModalityStatus.AVAILABLE
    face_detected: bool = True
    bounding_box: Optional[List[int]] = Field(None, description="[x1, y1, x2, y2]")
    identity: Optional[str] = None
    recognition_state: Optional[str] = None
    model_name: Optional[str] = None
    providers: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[float] = None
    identity_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    liveness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="PAD authenticity probability")
    deepfake_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Genuineness probability (1.0 = real)")
    quality: Optional[FaceQualityMetrics] = None
    reason_codes: List[str] = Field(default_factory=list)
