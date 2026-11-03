from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
from .face import FaceResult
from .voice import VoiceResult

class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    STEP_UP = "step_up"
    BLOCK = "block"
    ERROR = "error"

class AuthenticationResponse(BaseModel):
    session_id: str
    claimed_subject_id: Optional[str] = None
    overall_decision: DecisionOutcome
    fused_identity_score: float = Field(..., ge=0.0, le=1.0)
    fused_authenticity_score: float = Field(..., ge=0.0, le=1.0)
    reason_codes: List[str]
    face_result: FaceResult
    voice_result: VoiceResult
    latency_ms: int
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

