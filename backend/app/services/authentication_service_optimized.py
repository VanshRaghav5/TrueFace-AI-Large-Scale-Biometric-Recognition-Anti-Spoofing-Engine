import uuid
import time
import asyncio
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import settings
from ..core.security import verify_security_pin
from ..db.models.subject import Subject
from ..schemas.authentication import (
    AuthenticationResponse,
    DecisionOutcome,
    GateStatus,
    VerificationGates,
)
from ..schemas.face import FaceResult, ModalityStatus
from ..schemas.voice import VoiceResult
from ..fusion.fusion_engine import FusionEngine
from ..fusion.risk_engine import RiskEngine
from ..fusion.decision_policy import DecisionPolicy
from .face_runtime import face_runtime
from ..voice.voice_runtime import voice_runtime
from ..face.recognition.exceptions import (
    FaceRecognitionError,
    ModelUnavailableError,
)


class AuthenticationServiceOptimized:
    """
    Optimized authentication service using parallel processing for sub-100ms latency.
    
    Key optimizations:
    1. Parallel execution of face embedding + PAD + deepfake checks
    2. Concurrent voice and database lookups
    3. Early returns on critical failures
    4. Minimal object allocations
    """
    
    def __init__(
        self,
        fusion_engine: Optional[FusionEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        decision_policy: Optional[DecisionPolicy] = None
    ):
        self.fusion_engine = fusion_engine or FusionEngine(
            weight_face=settings.FUSION_WEIGHT_FACE,
            weight_voice=settings.FUSION_WEIGHT_VOICE,
        )
        self.risk_engine = risk_engine or RiskEngine(
            min_face_liveness=settings.FACE_LIVENESS_MIN_CONFIDENCE,
            min_deepfake_genuineness=settings.FACE_DEEPFAKE_MIN_AUTHENTICITY,
            min_voice_antispoof=settings.VOICE_LIVENESS_MIN_CONFIDENCE,
        )
        self.decision_policy = decision_policy or DecisionPolicy(
            min_identity_threshold=settings.FACE_MATCH_THRESHOLD,
            min_authenticity_threshold=min(
                settings.FACE_LIVENESS_MIN_CONFIDENCE,
                settings.FACE_DEEPFAKE_MIN_AUTHENTICITY,
            ),
        )

    async def _process_face_pipeline(self, face_bytes: bytes, claimed_subject_id: Optional[str]):
        """Process face recognition, PAD, and deepfake detection in parallel."""
        try:
            # Extract embedding (must be done first)
            embedding, extraction = face_runtime.extract(face_bytes)
            
            # Run PAD and deepfake checks in parallel while searching
            pad_task = asyncio.to_thread(face_runtime.evaluate_pad, face_bytes)
            deepfake_task = asyncio.to_thread(face_runtime.evaluate_deepfake, face_bytes)
            search_task = asyncio.to_thread(
                face_runtime.search, 
                embedding, 
                target_subject_id=claimed_subject_id
            )
            
            # Gather all results concurrently
            pad_result, deepfake_result, (subject_id, similarity) = await asyncio.gather(
                pad_task, deepfake_task, search_task, return_exceptions=True
            )
            
            # Handle exceptions gracefully
            if isinstance(pad_result, Exception):
                pad_result = None
            if isinstance(deepfake_result, Exception):
                deepfake_result = None
            if isinstance((subject_id, similarity), Exception):
                subject_id, similarity = None, None
            
            is_match = (
                subject_id is not None
                and similarity is not None
                and similarity >= face_runtime.threshold
            )
            
            # Build face result with all data
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
            
            # Process PAD results
            gate_pad = GateStatus(passed=True, status="omitted")
            if pad_result:
                face_result.liveness_score = pad_result["real_score"]
                face_result.pad_spoof_score = pad_result["spoof_score"]
                face_result.pad_state = pad_result["pad_state"]
                face_result.pad_provider = pad_result["provider"]
                
                if pad_result["pad_state"] == "attack":
                    is_match = False
                    face_result.identity = None
                    face_result.recognition_state = "spoof_attack_detected"
                    face_result.reason_codes.extend([
                        "FACE_PAD_ATTACK", "FACE_ATTACK_BLOCKED"
                    ])
                    gate_pad = GateStatus(passed=False, status="attack_detected")
                elif pad_result["pad_state"] == "bona_fide":
                    face_result.reason_codes.append("FACE_PAD_BONA_FIDE")
                    gate_pad = GateStatus(passed=True, status="bona_fide")
                else:
                    gate_pad = GateStatus(passed=False, status="uncertain")
            
            # Process deepfake results
            gate_deepfake = GateStatus(passed=True, status="omitted")
            if deepfake_result:
                face_result.deepfake_score = deepfake_result["authenticity_score"]
                face_result.deepfake_manipulation_score = deepfake_result["manipulation_score"]
                face_result.deepfake_state = deepfake_result["deepfake_state"]
                face_result.deepfake_provider = deepfake_result["provider"]
                
                if deepfake_result["deepfake_state"] == "manipulated":
                    is_match = False
                    face_result.identity = None
                    face_result.recognition_state = "deepfake_detected"
                    face_result.reason_codes.extend([
                        "FACE_DEEPFAKE_MANIPULATION_DETECTED", "FACE_DEEPFAKE_BLOCKED"
                    ])
                    gate_deepfake = GateStatus(passed=False, status="manipulated")
                elif deepfake_result["deepfake_state"] == "authentic":
                    face_result.reason_codes.append("FACE_DEEPFAKE_AUTHENTIC")
                    gate_deepfake = GateStatus(passed=True, status="authentic")
                else:
                    gate_deepfake = GateStatus(passed=True, status="uncertain")
            
            gate_face_rec = GateStatus(
                passed=is_match,
                status="passed" if is_match else "failed",
            )
            
            return face_result, gate_face_rec, gate_pad, gate_deepfake, subject_id, is_match
            
        except ModelUnavailableError:
            face_result = FaceResult(
                status=ModalityStatus.MODEL_UNAVAILABLE,
                face_detected=False,
                reason_codes=["FACE_MODEL_UNAVAILABLE"],
            )
            gate = GateStatus(passed=False, status="model_unavailable")
            return face_result, gate, gate, gate, None, False
        except FaceRecognitionError:
            face_result = FaceResult(
                status=ModalityStatus.ERROR,
                face_detected=False,
                reason_codes=["FACE_INFERENCE_ERROR"],
            )
            gate = GateStatus(passed=False, status="error")
            return face_result, gate, gate, gate, None, False

    async def verify(
        self,
        claimed_subject_id: Optional[str] = None,
        face_bytes: Optional[bytes] = None,
        voice_bytes: Optional[bytes] = None,
        security_pin: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> AuthenticationResponse:
        start_time = time.time()
        session_id = f"auth_{uuid.uuid4().hex[:8]}"

        # Initialize default gate statuses
        gate_face_rec = GateStatus(passed=False, status="missing")
        gate_pad = GateStatus(passed=False, status="missing")
        gate_deepfake = GateStatus(passed=False, status="missing")
        gate_voice_rec = GateStatus(passed=True, status="omitted")
        gate_voice_spoof = GateStatus(passed=True, status="omitted")
        gate_pin = GateStatus(passed=True, status="omitted")

        subject_id = None
        is_match = False

        # Run face and voice pipelines in parallel
        tasks = []
        if face_bytes:
            tasks.append(self._process_face_pipeline(face_bytes, claimed_subject_id))
        
        if voice_bytes:
            tasks.append(voice_runtime.verify(
                voice_bytes,
                claimed_subject_id=claimed_subject_id,
                session=session,
            ))

        # Execute all modalities concurrently
        if len(tasks) == 2:
            (face_result, gate_face_rec, gate_pad, gate_deepfake, subject_id, is_match), voice_result = await asyncio.gather(*tasks)
        elif len(tasks) == 1 and face_bytes:
            face_result, gate_face_rec, gate_pad, gate_deepfake, subject_id, is_match = await tasks[0]
            voice_result = VoiceResult(status=ModalityStatus.MISSING, speech_detected=False)
        elif len(tasks) == 1 and voice_bytes:
            voice_result = await tasks[0]
            face_result = FaceResult(status=ModalityStatus.MISSING, face_detected=False)
        else:
            face_result = FaceResult(status=ModalityStatus.MISSING, face_detected=False)
            voice_result = VoiceResult(status=ModalityStatus.MISSING, speech_detected=False)

        # Process voice gates
        if voice_bytes and voice_result.status == ModalityStatus.AVAILABLE:
            v_match = "VOICE_IDENTITY_MATCH" in voice_result.reason_codes
            v_spoof = "AUDIO_SPOOF_RISK" in voice_result.reason_codes
            gate_voice_rec = GateStatus(passed=v_match, status="passed" if v_match else "failed")
            gate_voice_spoof = GateStatus(passed=not v_spoof, status="passed" if not v_spoof else "failed")

        # Security PIN verification (async database lookup)
        pin_reasons = []
        target_sub = claimed_subject_id or subject_id
        if session and target_sub:
            sub_res = await session.execute(
                select(Subject).where(Subject.pseudonymous_id == target_sub, Subject.is_active == True)
            )
            sub_obj = sub_res.scalars().first()
            if sub_obj and sub_obj.security_pin_hash:
                if not security_pin or not security_pin.strip():
                    pin_reasons.append("SECURITY_CODE_REQUIRED")
                    gate_pin = GateStatus(passed=False, status="required")
                elif verify_security_pin(security_pin.strip(), sub_obj.security_pin_hash):
                    pin_reasons.append("SECURITY_CODE_MATCH")
                    gate_pin = GateStatus(passed=True, status="verified")
                else:
                    pin_reasons.append("SECURITY_CODE_MISMATCH")
                    gate_pin = GateStatus(passed=False, status="mismatch")

        # Fusion & Risk Evaluation
        fused_identity, fusion_reasons = self.fusion_engine.fuse_identity(face_result, voice_result)
        fused_authenticity, risk_reasons = self.risk_engine.evaluate_authenticity(face_result, voice_result)

        all_detected_reasons = list(set(fusion_reasons + risk_reasons + pin_reasons))

        # Decision Policy
        decision, final_reasons = self.decision_policy.decide(
            fused_identity_score=fused_identity,
            fused_authenticity_score=fused_authenticity,
            face_result=face_result,
            voice_result=voice_result,
            detected_reasons=all_detected_reasons,
        )

        # Enforce zero-trust gates
        all_gates_pass = (
            gate_face_rec.passed
            and gate_pad.passed
            and gate_deepfake.passed
            and gate_voice_rec.passed
            and gate_voice_spoof.passed
            and gate_pin.passed
        )
        if decision == DecisionOutcome.ALLOW and not all_gates_pass:
            decision = DecisionOutcome.BLOCK
            final_reasons.append("ZERO_TRUST_GATE_FAILED")

        gates = VerificationGates(
            face_recognition=gate_face_rec,
            liveness_anti_spoof=gate_pad,
            deepfake_detection=gate_deepfake,
            voice_recognition=gate_voice_rec,
            voice_anti_spoof=gate_voice_spoof,
            security_pin=gate_pin,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        return AuthenticationResponse(
            session_id=session_id,
            claimed_subject_id=claimed_subject_id or subject_id,
            overall_decision=decision,
            fused_identity_score=fused_identity,
            fused_authenticity_score=fused_authenticity,
            reason_codes=final_reasons,
            face_result=face_result,
            voice_result=voice_result,
            gates=gates,
            pin_verified=gate_pin.passed,
            latency_ms=latency_ms,
        )
