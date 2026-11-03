import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False, index=True)
    claimed_subject_id = Column(String(64), nullable=True)
    overall_decision = Column(String(16), nullable=False)
    reason_codes = Column(JSON, nullable=False, default=list)
    face_similarity = Column(Float, nullable=True)
    face_liveness = Column(Float, nullable=True)
    voice_similarity = Column(Float, nullable=True)
    voice_antispoof = Column(Float, nullable=True)
    fused_score = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

