import uuid
import time
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

class AuthenticationService:
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

        gate_face_rec = GateStatus(passed=False, status="missing", detail="Face image not provided")
        gate_pad = GateStatus(passed=False, status="missing", detail="Liveness evaluation omitted")
        gate_deepfake = GateStatus(passed=False, status="missing", detail="Deepfake check omitted")
        gate_voice_rec = GateStatus(passed=True, status="omitted", detail="Voice modality not required")
        gate_voice_spoof = GateStatus(passed=True, status="omitted", detail="Voice anti-spoof not required")
        gate_pin = GateStatus(passed=True, status="omitted", detail="Security PIN not required")

        is_match = False
        subject_id = None
        face_reasons = []

        # 1. Face Pipeline (ArcFace Recognition + MiniFASNet PAD + DeepfakeBench)
        if face_bytes:
            try:
                embedding, extraction = face_runtime.extract(face_bytes)
                subject_id, similarity = face_runtime.search(
                    embedding, target_subject_id=claimed_subject_id
                )
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
                gate_face_rec = GateStatus(
                    passed=is_match,
                    status="passed" if is_match else "failed",
                    detail=f"Identity: {subject_id} (sim: {similarity:.3f})" if similarity is not None else "No match",
                )

                # Gate 2: Presentation Attack Detection (Liveness / Anti-Spoofing)
                try:
                    pad = face_runtime.evaluate_pad(face_bytes)
                    face_result.liveness_score = pad["real_score"]
                    face_result.pad_spoof_score = pad["spoof_score"]
                    face_result.pad_state = pad["pad_state"]
                    face_result.pad_provider = pad["provider"]
                    if pad["pad_state"] == "attack":
                        is_match = False
                        face_result.identity = None
                        face_result.recognition_state = "spoof_attack_detected"
                        face_result.reason_codes.extend([
                            "FACE_PAD_ATTACK",
                            "FACE_PAD_RISK",
                            "FACE_ATTACK_BLOCKED",
                            "BIOMETRIC_SPOOF_REJECTED",
                        ])
                        gate_pad = GateStatus(passed=False, status="attack_detected", detail=f"Spoof score: {pad['spoof_score']:.3f}")
                    elif pad["pad_state"] == "bona_fide":
                        face_result.reason_codes.append("FACE_PAD_BONA_FIDE")
                        gate_pad = GateStatus(passed=True, status="bona_fide", detail=f"Live score: {pad['real_score']:.3f}")
                    elif pad["pad_state"] == "uncertain":
                        face_result.reason_codes.append("FACE_PAD_UNCERTAIN")
                        gate_pad = GateStatus(passed=False, status="uncertain", detail="Uncertain liveness")
                    else:
                        face_result.reason_codes.append("FACE_PAD_THRESHOLD_UNCALIBRATED")
                        gate_pad = GateStatus(passed=True, status="uncalibrated")
                except ModelUnavailableError:
                    face_result.reason_codes.append("FACE_PAD_UNAVAILABLE")
                    gate_pad = GateStatus(passed=True, status="model_unavailable")
                except FaceRecognitionError:
                    face_result.reason_codes.append("FACE_PAD_EVALUATION_ERROR")
                    gate_pad = GateStatus(passed=False, status="error")

                # Gate 3: Deepfake Detection Check (DeepfakeBench)
                try:
                    deepfake = face_runtime.evaluate_deepfake(face_bytes)
                    face_result.deepfake_score = deepfake["authenticity_score"]
                    face_result.deepfake_manipulation_score = deepfake["manipulation_score"]
                    face_result.deepfake_state = deepfake["deepfake_state"]
                    face_result.deepfake_provider = deepfake["provider"]
                    if deepfake["deepfake_state"] == "manipulated" or deepfake.get("is_deepfake"):
                        is_match = False
                        face_result.identity = None
                        face_result.recognition_state = "deepfake_detected"
                        face_result.reason_codes.extend([
                            "FACE_DEEPFAKE_MANIPULATION_DETECTED",
                            "FACE_MANIPULATION_RISK",
                            "FACE_DEEPFAKE_BLOCKED",
                        ])
                        gate_deepfake = GateStatus(passed=False, status="manipulated", detail=f"Manipulation score: {deepfake['manipulation_score']:.3f}")
                    elif deepfake["deepfake_state"] == "authentic":
                        face_result.reason_codes.append("FACE_DEEPFAKE_AUTHENTIC")
                        gate_deepfake = GateStatus(passed=True, status="authentic", detail=f"Authenticity: {deepfake['authenticity_score']:.3f}")
                    else:
                        # uncertain: pass the gate — do not block on ambiguity
                        face_result.reason_codes.append("FACE_DEEPFAKE_UNCERTAIN")
                        gate_deepfake = GateStatus(passed=True, status="uncertain", detail=f"Uncertain: real={deepfake['authenticity_score']:.3f}")
                except ModelUnavailableError:
                    face_result.reason_codes.append("FACE_DEEPFAKE_MODEL_UNAVAILABLE")
                    gate_deepfake = GateStatus(passed=True, status="model_unavailable")
                except FaceRecognitionError:
                    face_result.reason_codes.append("FACE_DEEPFAKE_EVALUATION_ERROR")
                    gate_deepfake = GateStatus(passed=False, status="error")

            except ModelUnavailableError:
                face_result = FaceResult(
                    status=ModalityStatus.MODEL_UNAVAILABLE,
                    face_detected=False,
                    reason_codes=["FACE_MODEL_UNAVAILABLE"],
                )
                gate_face_rec = GateStatus(passed=False, status="model_unavailable")
            except FaceRecognitionError:
                face_result = FaceResult(
                    status=ModalityStatus.ERROR,
                    face_detected=False,
                    reason_codes=["FACE_INFERENCE_ERROR"],
                )
                gate_face_rec = GateStatus(passed=False, status="error")
        else:
            face_result = FaceResult(status=ModalityStatus.MISSING, face_detected=False)

        # 2. Voice Pipeline (Gate 4: Speaker Verification + Gate 5: Audio Anti-Spoofing)
        if voice_bytes:
            voice_result = await voice_runtime.verify(
                voice_bytes,
                claimed_subject_id=claimed_subject_id or subject_id,
                session=session,
            )
            v_match = "VOICE_IDENTITY_MATCH" in voice_result.reason_codes
            v_spoof = "AUDIO_SPOOF_RISK" in voice_result.reason_codes
            gate_voice_rec = GateStatus(
                passed=v_match,
                status="passed" if v_match else "failed",
                detail=f"Voice sim: {voice_result.identity_similarity:.3f}" if voice_result.identity_similarity is not None else "No enrolled template",
            )
            gate_voice_spoof = GateStatus(
                passed=not v_spoof,
                status="failed" if v_spoof else "passed",
                detail=f"Speech genuine prob: {voice_result.antispoof_score:.3f}" if voice_result.antispoof_score is not None else "Evaluated",
            )
        else:
            voice_result = VoiceResult(status=ModalityStatus.MISSING, speech_detected=False)

        # 3. Security PIN / Final Passcode Verification (Gate 6)
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
                    gate_pin = GateStatus(passed=False, status="required", detail="Enrolled security PIN was not provided")
                elif verify_security_pin(security_pin.strip(), sub_obj.security_pin_hash):
                    pin_reasons.append("SECURITY_CODE_MATCH")
                    gate_pin = GateStatus(passed=True, status="verified", detail="Security PIN matched")
                else:
                    pin_reasons.append("SECURITY_CODE_MISMATCH")
                    gate_pin = GateStatus(passed=False, status="mismatch", detail="Incorrect security PIN")
            elif settings.REQUIRE_SECURITY_PIN and not security_pin:
                pin_reasons.append("SECURITY_CODE_REQUIRED")
                gate_pin = GateStatus(passed=False, status="required", detail="Security PIN required by system policy")
            else:
                pin_reasons.append("SECURITY_CODE_NOT_ENROLLED")
                gate_pin = GateStatus(passed=True, status="not_enrolled", detail="Subject has no enrolled PIN")
        elif settings.REQUIRE_SECURITY_PIN and not security_pin:
            pin_reasons.append("SECURITY_CODE_REQUIRED")
            gate_pin = GateStatus(passed=False, status="required", detail="Security PIN required")

        # 4. Fusion & Risk Evaluation
        fused_identity, fusion_reasons = self.fusion_engine.fuse_identity(face_result, voice_result)
        fused_authenticity, risk_reasons = self.risk_engine.evaluate_authenticity(face_result, voice_result)

        all_detected_reasons = list(set(fusion_reasons + risk_reasons + pin_reasons))

        # 5. Multi-Gate Zero-Trust Decision Policy
        decision, final_reasons = self.decision_policy.decide(
            fused_identity_score=fused_identity,
            fused_authenticity_score=fused_authenticity,
            face_result=face_result,
            voice_result=voice_result,
            detected_reasons=all_detected_reasons,
        )

        # Enforce all gates must pass for final ALLOW
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
