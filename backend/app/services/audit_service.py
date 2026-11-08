from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas.authentication import AuthenticationResponse
from ..db.repositories.audit_repository import AuditRepository

class AuditService:
    async def record_verification(
        self,
        auth_response: AuthenticationResponse,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        event = {
            "session_id": auth_response.session_id,
            "claimed_subject_id": auth_response.claimed_subject_id,
            "overall_decision": auth_response.overall_decision.value,
            "reason_codes": auth_response.reason_codes,
            "face_similarity": auth_response.face_result.identity_similarity,
            "face_liveness": auth_response.face_result.liveness_score,
            "face_pad_spoof": auth_response.face_result.pad_spoof_score,
            "voice_similarity": auth_response.voice_result.identity_similarity,
            "voice_antispoof": auth_response.voice_result.antispoof_score,
            "fused_score": auth_response.fused_identity_score,
            "latency_ms": auth_response.latency_ms,
            "created_at": auth_response.evaluated_at,
        }
        stored = await AuditRepository(session).log_event(event)
        return {
            "session_id": stored.session_id,
            "claimed_subject_id": stored.claimed_subject_id,
            "overall_decision": stored.overall_decision,
            "reason_codes": stored.reason_codes,
            "face_similarity": stored.face_similarity,
            "face_liveness": stored.face_liveness,
            "face_pad_spoof": stored.face_pad_spoof,
            "voice_similarity": stored.voice_similarity,
            "voice_antispoof": stored.voice_antispoof,
            "fused_score": stored.fused_score,
            "latency_ms": stored.latency_ms,
            "timestamp": stored.created_at.isoformat(),
        }

    async def get_recent_events(
        self,
        session: AsyncSession,
        limit: int = 50,
        decision: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        events = await AuditRepository(session).list_events(
            limit=limit,
            decision=decision,
        )
        return [
            {
                "session_id": event.session_id,
                "claimed_subject_id": event.claimed_subject_id,
                "overall_decision": event.overall_decision,
                "reason_codes": event.reason_codes,
                "face_similarity": event.face_similarity,
                "face_liveness": event.face_liveness,
                "face_pad_spoof": event.face_pad_spoof,
                "voice_similarity": event.voice_similarity,
                "voice_antispoof": event.voice_antispoof,
                "fused_score": event.fused_score,
                "latency_ms": event.latency_ms,
                "timestamp": event.created_at.isoformat(),
            }
            for event in events
        ]
