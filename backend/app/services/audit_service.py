from typing import List, Dict, Any
from ..schemas.authentication import AuthenticationResponse

class AuditService:
    def __init__(self):
        self._in_memory_events: List[Dict[str, Any]] = []

    async def record_verification(self, auth_response: AuthenticationResponse):
        # Privacy check: Record only metadata, scores, and reason codes
        event = {
            "session_id": auth_response.session_id,
            "claimed_subject_id": auth_response.claimed_subject_id,
            "overall_decision": auth_response.overall_decision.value,
            "reason_codes": auth_response.reason_codes,
            "fused_score": auth_response.fused_identity_score,
            "latency_ms": auth_response.latency_ms,
            "timestamp": auth_response.evaluated_at.isoformat()
        }
        self._in_memory_events.append(event)
        return event

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._in_memory_events[-limit:]

