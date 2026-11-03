from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.subject import Subject

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

