from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.subject import Subject
from ..models.template import BiometricTemplate

class SubjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pseudonymous_id(self, pseudonymous_id: str) -> Optional[Subject]:
        stmt = select(Subject).where(Subject.pseudonymous_id == pseudonymous_id, Subject.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, pseudonymous_id: str, consent_granted: bool) -> Subject:
        subject = Subject(
            pseudonymous_id=pseudonymous_id,
            consent_granted=consent_granted
        )
        self.session.add(subject)
        await self.session.flush()
        return subject

    async def get_or_create(self, pseudonymous_id: str, consent_granted: bool) -> Subject:
        subject = await self.get_by_pseudonymous_id(pseudonymous_id)
        if subject:
            if consent_granted and not subject.consent_granted:
                subject.consent_granted = True
            return subject
        return await self.create(pseudonymous_id, consent_granted)

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Subject).where(Subject.is_active == True)
        )
        return int(result.scalar_one())

    async def get_face_templates(self) -> list[BiometricTemplate]:
        result = await self.session.execute(
            select(BiometricTemplate, Subject.pseudonymous_id)
            .join(Subject, BiometricTemplate.subject_id == Subject.id)
            .where(
                Subject.is_active == True,
                BiometricTemplate.modality == "FACE",
            )
        )
        return [row[0] for row in result.all()]

    async def get_face_templates_with_subjects(self):
        result = await self.session.execute(
            select(BiometricTemplate, Subject.pseudonymous_id)
            .join(Subject, BiometricTemplate.subject_id == Subject.id)
            .where(
                Subject.is_active == True,
                BiometricTemplate.modality == "FACE",
            )
        )
        return list(result.all())
