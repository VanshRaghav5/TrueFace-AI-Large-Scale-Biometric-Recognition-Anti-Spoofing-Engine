from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ....services.audit_service import AuditService
from ....db.database import get_db

router = APIRouter()
audit_service = AuditService()

@router.get("/events")
async def get_audit_events(
    limit: int = Query(20, ge=1, le=100),
    decision: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    events = await audit_service.get_recent_events(
        session=session,
        limit=limit,
        decision=decision,
    )
    return {
        "total": len(events),
        "items": events
    }
