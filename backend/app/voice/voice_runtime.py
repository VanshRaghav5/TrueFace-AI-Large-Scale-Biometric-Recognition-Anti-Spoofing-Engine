"""Voice runtime for speaker verification and audio anti-spoofing."""

from __future__ import annotations

import hashlib
from typing import Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models.subject import Subject
from ..db.models.template import BiometricTemplate
from ..schemas.voice import AudioQualityMetrics, VoiceResult, ModalityStatus
from .anti_spoofing.voice_antispoof import evaluate_audio_antispoof
from .speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    VoiceProcessingError,
    compute_voice_similarity,
    extract_acoustic_embedding,
    parse_wav_bytes,
)


class VoiceRuntime:
    """Manages voice feature extraction, gallery comparison, and anti-spoofing."""

    def __init__(self) -> None:
        self.model_name = "acoustic_filterbank_128"
        self.model_version = "v1"
        self.dimension = 128

    def extract(self, voice_bytes: bytes) -> Tuple[np.ndarray, AudioQualityMetrics]:
        """Parse WAV, validate biometric quality, and extract normalized 128-dim embedding."""
        samples, sr, props = parse_wav_bytes(voice_bytes)
        embedding = extract_acoustic_embedding(samples, sr, dim=self.dimension)
        metrics = AudioQualityMetrics(
            duration_seconds=props.duration_seconds,
            speech_ratio=props.speech_ratio,
            snr_db=props.snr_db,
        )
        return embedding, metrics

    async def verify(
        self,
        voice_bytes: bytes,
        claimed_subject_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> VoiceResult:
        """Evaluate speaker verification against claimed subject's enrolled voice template."""
        try:
            samples, sr, props = parse_wav_bytes(voice_bytes)
        except InvalidAudioError as exc:
            return VoiceResult(
                status=ModalityStatus.INVALID,
                speech_detected=False,
                reason_codes=[f"VOICE_DECODE_ERROR:{str(exc)}"],
            )
        except AudioQualityError as exc:
            return VoiceResult(
                status=ModalityStatus.LOW_QUALITY,
                speech_detected=False,
                reason_codes=[f"VOICE_QUALITY_LOW:{str(exc)}"],
            )

        embedding = extract_acoustic_embedding(samples, sr, dim=self.dimension)
        quality = AudioQualityMetrics(
            duration_seconds=props.duration_seconds,
            speech_ratio=props.speech_ratio,
            snr_db=props.snr_db,
        )

        # Anti-spoof check
        antispoof_res = evaluate_audio_antispoof(
            samples, sr, min_confidence=settings.VOICE_LIVENESS_MIN_CONFIDENCE
        )

        reason_codes = []
        similarity = None
        is_match = False

        if antispoof_res.is_synthetic_speech:
            reason_codes.append("AUDIO_SPOOF_RISK")
            reason_codes.append("VOICE_SYNTHETIC_SPEECH_DETECTED")
        else:
            reason_codes.append("VOICE_ANTISPOOF_BONA_FIDE")

        # Identity matching against database enrolled voice template
        if session and claimed_subject_id:
            result = await session.execute(
                select(BiometricTemplate)
                .join(Subject, BiometricTemplate.subject_id == Subject.id)
                .where(
                    Subject.pseudonymous_id == claimed_subject_id,
                    Subject.is_active == True,
                    BiometricTemplate.modality == "VOICE",
                )
            )
            template = result.scalars().first()
            if template and template.embedding:
                stored_vec = np.frombuffer(template.embedding, dtype=np.float32)
                similarity = compute_voice_similarity(embedding, stored_vec)
                if similarity >= settings.VOICE_MATCH_THRESHOLD and not antispoof_res.is_synthetic_speech:
                    is_match = True
                    reason_codes.append("VOICE_IDENTITY_MATCH")
                else:
                    reason_codes.append("VOICE_IDENTITY_MISMATCH")
            else:
                reason_codes.append("VOICE_TEMPLATE_NOT_ENROLLED")
        elif not claimed_subject_id:
            reason_codes.append("VOICE_CLAIMED_IDENTITY_OMITTED")

        return VoiceResult(
            status=ModalityStatus.AVAILABLE,
            speech_detected=props.speech_ratio > 0.25,
            identity_similarity=similarity,
            antispoof_score=antispoof_res.genuine_probability,
            quality=quality,
            reason_codes=reason_codes,
        )

    def evaluate_antispoof(self, voice_bytes: bytes) -> dict:
        """Standalone voice presentation attack and synthetic speech evaluation."""
        samples, sr, props = parse_wav_bytes(voice_bytes)
        result = evaluate_audio_antispoof(
            samples, sr, min_confidence=settings.VOICE_LIVENESS_MIN_CONFIDENCE
        )
        return {
            "status": "available",
            "speech_detected": props.speech_ratio > 0.25,
            "duration_seconds": props.duration_seconds,
            "genuine_probability": result.genuine_probability,
            "spoof_probability": result.spoof_probability,
            "is_synthetic_speech": result.is_synthetic_speech,
            "state": result.state,
            "details": result.details,
        }


voice_runtime = VoiceRuntime()

