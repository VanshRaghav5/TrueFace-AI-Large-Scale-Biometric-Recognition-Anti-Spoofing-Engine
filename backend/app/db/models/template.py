import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from ..database import Base

class BiometricTemplate(Base):
    __tablename__ = "biometric_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    modality = Column(String(16), nullable=False)  # "FACE" | "VOICE"
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=False)
    vector_store_index = Column(Integer, nullable=True)
    template_hash = Column(String(64), nullable=False)
    embedding = Column(LargeBinary, nullable=False)
    embedding_dimension = Column(Integer, nullable=False, default=512)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
