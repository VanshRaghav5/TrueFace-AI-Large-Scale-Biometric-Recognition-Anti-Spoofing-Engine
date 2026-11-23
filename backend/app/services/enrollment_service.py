import hashlib
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.exceptions import ConsentRequiredError
from ..core.security import hash_security_pin
from ..schemas.enrollment import EnrollmentResponse
from .face_runtime import face_runtime
from ..voice.voice_runtime import voice_runtime
from ..db.models.subject import Subject
from ..db.models.template import BiometricTemplate
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
                "has_pin": bool(subject.security_pin_hash),
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
        voice_bytes: Optional[bytes] = None,
        security_pin: Optional[str] = None,
    ) -> EnrollmentResponse:
        if not consent_confirmed:
            raise ConsentRequiredError("Enrollment rejected: Explicit subject consent must be confirmed.")

        if not face_bytes:
            raise ValueError("A face image is required for face enrollment")

        subject, result, created = await face_runtime.enroll(
            session, subject_id, consent_confirmed, face_bytes
        )

        voice_enrolled = False
        if voice_bytes:
            voice_vec, _ = voice_runtime.extract(voice_bytes)
            # Remove any previous voice template for this subject
            existing_voice = await session.execute(
                select(BiometricTemplate).where(
                    BiometricTemplate.subject_id == subject.id,
                    BiometricTemplate.modality == "VOICE",
                )
            )
            for v_tmpl in existing_voice.scalars().all():
                await session.delete(v_tmpl)

            voice_tmpl = BiometricTemplate(
                id=uuid.uuid4(),
                subject_id=subject.id,
                modality="VOICE",
                model_name=voice_runtime.model_name,
                model_version=voice_runtime.model_version,
                vector_store_index=None,
                template_hash=hashlib.sha256(voice_vec.tobytes()).hexdigest(),
                embedding=voice_vec.tobytes(),
                embedding_dimension=voice_runtime.dimension,
                created_at=datetime.utcnow(),
            )
            session.add(voice_tmpl)
            voice_enrolled = True

        pin_enrolled = False
        if security_pin and security_pin.strip():
            subject.security_pin_hash = hash_security_pin(security_pin.strip())
            pin_enrolled = True

        await session.flush()

        # Count total templates for this subject
        tmpl_count_res = await session.execute(
            select(BiometricTemplate).where(BiometricTemplate.subject_id == subject.id)
        )
        total_templates = len(tmpl_count_res.scalars().all())

        return EnrollmentResponse(
            enrollment_id=str(subject.id),
            subject_id=subject_id,
            status="enrolled" if created else "updated",
            face_enrolled=True,
            voice_enrolled=voice_enrolled,
            pin_enrolled=pin_enrolled,
            template_count=total_templates,
            detail=(
                f"{result.model_name} enrolled. Multi-factor credentials registered."
                if created else "Subject credentials updated successfully"
            ),
        )
