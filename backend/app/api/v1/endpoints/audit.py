from fastapi import APIRouter, Query
from typing import Optional
from ....services.audit_service import AuditService

router = APIRouter()
audit_service = AuditService()

@router.get("/events")
async def get_audit_events(
    limit: int = Query(20, ge=1, le=100),
    decision: Optional[str] = Query(None)
):
    events = await audit_service.get_recent_events(limit=limit)
    if decision:
        events = [e for e in events if e.get("overall_decision") == decision]
    return {
        "total": len(events),
        "items": events
    }

