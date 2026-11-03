from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..models.audit import AuditEvent

class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(self, event_data: dict) -> AuditEvent:
        event = AuditEvent(**event_data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(self, limit: int = 50, offset: int = 0) -> List[AuditEvent]:
        stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

