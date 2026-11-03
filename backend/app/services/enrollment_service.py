from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.exceptions import ConsentRequiredError
from ..schemas.enrollment import EnrollmentResponse
from .face_runtime import face_runtime
from ..db.models.subject import Subject
from sqlalchemy import select

class EnrollmentService:
    async def list_subjects(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(Subject).where(Subject.is_active == True).order_by(Subject.created_at)
        )
        return [
            {
                "subject_id": subject.pseudonymous_id,
                "consent_granted": subject.consent_granted,
                "created_at": subject.created_at,
            }
            for subject in result.scalars().all()
        ]

    async def delete_subject(self, session: AsyncSession, subject_id: str) -> bool:
        result = await session.execute(
            select(Subject).where(
                Subject.pseudonymous_id == subject_id,
                Subject.is_active == True,
            )
        )
        subject = result.scalars().first()
        if subject is None:
            return False
        subject.is_active = False
        await session.flush()
        await face_runtime.hydrate(session)
        return True

    async def enroll_subject(
        self,
        session: AsyncSession,
        subject_id: str,
        consent_confirmed: bool,
        face_bytes: Optional[bytes] = None,
        voice_bytes: Optional[bytes] = None
    ) -> EnrollmentResponse:
        if not consent_confirmed:
            raise ConsentRequiredError("Enrollment rejected: Explicit subject consent must be confirmed.")

        if voice_bytes:
            raise ValueError("Voice enrollment is unavailable until an authorized voice model is configured")
        if not face_bytes:
            raise ValueError("A face image is required for face enrollment")
        subject, result, created = await face_runtime.enroll(
            session, subject_id, consent_confirmed, face_bytes
        )
        return EnrollmentResponse(
            enrollment_id=str(subject.id),
            subject_id=subject_id,
            status="enrolled" if created else "duplicate",
            face_enrolled=True,
            voice_enrolled=False,
            template_count=face_runtime.status.template_count,
            detail=(
                f"{result.model_name} detected one face"
                if created else "This face template is already enrolled"
            ),
        )
