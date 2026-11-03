import uuid
import time
from typing import Optional
from ..schemas.authentication import AuthenticationResponse, DecisionOutcome
from ..schemas.face import FaceResult, ModalityStatus
from ..schemas.voice import VoiceResult
from ..fusion.fusion_engine import FusionEngine
from ..fusion.risk_engine import RiskEngine
from ..fusion.decision_policy import DecisionPolicy
from .face_runtime import face_runtime
from ..face.recognition.exceptions import (
    FaceRecognitionError,
    ModelUnavailableError,
)

class AuthenticationService:
    def __init__(
        self,
        fusion_engine: Optional[FusionEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        decision_policy: Optional[DecisionPolicy] = None
    ):
        self.fusion_engine = fusion_engine or FusionEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.decision_policy = decision_policy or DecisionPolicy()

    async def verify(
        self,
        claimed_subject_id: Optional[str] = None,
        face_bytes: Optional[bytes] = None,
        voice_bytes: Optional[bytes] = None
    ) -> AuthenticationResponse:
        start_time = time.time()
        session_id = f"auth_{uuid.uuid4().hex[:8]}"

        if face_bytes:
            try:
                embedding, extraction = face_runtime.extract(face_bytes)
                subject_id, similarity = face_runtime.search(embedding)
                is_match = (
                    subject_id is not None
                    and similarity is not None
                    and similarity >= face_runtime.threshold
                )
                face_result = FaceResult(
                    status=ModalityStatus.AVAILABLE,
                    face_detected=True,
                    bounding_box=extraction.bounding_box,
                    identity=subject_id if is_match else None,
                    recognition_state="known" if is_match else "unknown",
                    identity_similarity=max(0.0, similarity) if similarity is not None else None,
                    model_name=extraction.model_name,
                    providers=face_runtime.status.providers,
                    processing_time_ms=extraction.inference_time_ms,
                    reason_codes=["FACE_IDENTITY_MATCH" if is_match else "FACE_IDENTITY_UNKNOWN"],
                )
            except ModelUnavailableError:
                face_result = FaceResult(
                    status=ModalityStatus.MODEL_UNAVAILABLE,
                    face_detected=False,
                    reason_codes=["FACE_MODEL_UNAVAILABLE"],
                )
            except FaceRecognitionError:
                face_result = FaceResult(
                    status=ModalityStatus.ERROR,
                    face_detected=False,
                    reason_codes=["FACE_INFERENCE_ERROR"],
                )
        else:
            face_result = FaceResult(status=ModalityStatus.MISSING, face_detected=False)

        # 2. Process Voice Pipeline
        if voice_bytes:
            voice_result = VoiceResult(
                status=ModalityStatus.MODEL_UNAVAILABLE,
                speech_detected=False,
                reason_codes=["VOICE_MODEL_UNAVAILABLE"],
            )
        else:
            voice_result = VoiceResult(status=ModalityStatus.MISSING, speech_detected=False)

        # 3. Fusion & Risk Evaluation
        fused_identity, fusion_reasons = self.fusion_engine.fuse_identity(face_result, voice_result)
        fused_authenticity, risk_reasons = self.risk_engine.evaluate_authenticity(face_result, voice_result)

        all_detected_reasons = list(set(fusion_reasons + risk_reasons))

        # 4. Decision Policy
        decision, final_reasons = self.decision_policy.decide(
            fused_identity_score=fused_identity,
            fused_authenticity_score=fused_authenticity,
            face_result=face_result,
            voice_result=voice_result,
            detected_reasons=all_detected_reasons
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return AuthenticationResponse(
            session_id=session_id,
            claimed_subject_id=claimed_subject_id,
            overall_decision=decision,
            fused_identity_score=fused_identity,
            fused_authenticity_score=fused_authenticity,
            reason_codes=final_reasons,
            face_result=face_result,
            voice_result=voice_result,
            latency_ms=latency_ms
        )
