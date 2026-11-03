from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EnrollmentResponse(BaseModel):
    enrollment_id: str
    subject_id: str
    status: str
    face_enrolled: bool
    voice_enrolled: bool
    template_count: int = 0
    detail: Optional[str] = None
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
