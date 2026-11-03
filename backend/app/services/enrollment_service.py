import uuid
from typing import Optional
import numpy as np
from ..core.exceptions import ConsentRequiredError, BiometricQualityError
from ..schemas.enrollment import EnrollmentResponse
from ..search.faiss_store import FAISSStore

class EnrollmentService:
    def __init__(self, vector_store: Optional[FAISSStore] = None):
        self.vector_store = vector_store or FAISSStore()

    async def enroll_subject(
        self,
        subject_id: str,
        consent_confirmed: bool,
        face_bytes: Optional[bytes] = None,
        voice_bytes: Optional[bytes] = None
    ) -> EnrollmentResponse:
        if not consent_confirmed:
            raise ConsentRequiredError("Enrollment rejected: Explicit subject consent must be confirmed.")

        face_enrolled = False
        voice_enrolled = False

        if face_bytes:
            # Generate normalized face embedding placeholder/stub
            dummy_face_embedding = np.random.randn(512).astype("float32")
            dummy_face_embedding /= np.linalg.norm(dummy_face_embedding)
            self.vector_store.add_vector(dummy_face_embedding, subject_id)
            face_enrolled = True

        if voice_bytes:
            voice_enrolled = True

        return EnrollmentResponse(
            enrollment_id=f"enr_{uuid.uuid4().hex[:8]}",
            subject_id=subject_id,
            status="success",
            face_enrolled=face_enrolled,
            voice_enrolled=voice_enrolled
        )

