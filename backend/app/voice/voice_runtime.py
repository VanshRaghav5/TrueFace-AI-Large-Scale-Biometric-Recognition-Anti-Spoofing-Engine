"""Voice runtime for speaker verification and audio anti-spoofing.

Speaker identity is verified with the SpeechBrain ECAPA-TDNN encoder: an audio
sample is decoded, quality-checked, encoded into a normalized speaker embedding,
compared (cosine) against the subject's enrolled voice template, and screened by
the audio anti-spoofing analyzer. The encoder is loaded once at startup and reused
for every request.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models.subject import Subject
from ..db.models.template import BiometricTemplate
from ..schemas.voice import AudioQualityMetrics, ModalityStatus, VoiceResult
from .anti_spoofing.voice_antispoof import (
    AntispoofModelUnavailableError,
    evaluate_audio_antispoof,
    get_antispoof_detector,
)
from .speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    SpeakerModelUnavailableError,
    VoiceProcessingError,
    compute_voice_similarity,
    get_speaker_embedder,
    parse_wav_bytes,
)


@dataclass
class VoiceRuntimeStatus:
    initialized: bool = False
    model_name: str = "ecapa_tdnn_voxceleb"
    model_version: str = "v1"
    dimension: int = 192
    model_source: Optional[str] = None
    error: Optional[str] = None
    antispoof_initialized: bool = False
    antispoof_model_name: str = "aasist"
    antispoof_error: Optional[str] = None


class VoiceRuntime:
    """Manages voice feature extraction, gallery comparison, and anti-spoofing."""

    def __init__(self) -> None:
        self._embedder = get_speaker_embedder()
        self.model_name = self._embedder.model_name
        self.model_version = self._embedder.model_version
        self.dimension = settings.VOICE_EMBEDDING_DIMENSION
        self.status = VoiceRuntimeStatus(
            model_name=self.model_name,
            model_version=self.model_version,
            dimension=self.dimension,
            model_source=settings.VOICE_SPEAKER_HF_SOURCE,
        )

    def initialize(self) -> VoiceRuntimeStatus:
        """Load the speaker encoder and anti-spoofing model eagerly.

        Safe to call at app startup. Failure (missing package, unreachable
        weights) is recorded on the status and does not raise, so the rest of
        the API stays available. Speaker requests degrade to an explicit
        ``model_unavailable`` state; anti-spoofing falls back to an explicitly
        labeled acoustic-spectral heuristic.
        """
        try:
            self._embedder.load()
            self.dimension = self._embedder.dimension
            self.model_name = self._embedder.model_name
            self.model_version = self._embedder.model_version
            self.status.initialized = True
            self.status.dimension = self.dimension
            self.status.model_name = self.model_name
            self.status.model_version = self.model_version
            self.status.error = None
        except SpeakerModelUnavailableError as exc:
            self.status.initialized = False
            self.status.error = exc.args[0] if exc.args else str(exc)
        except Exception as exc:  # defensive: never crash startup over a model
            self.status.initialized = False
            self.status.error = f"Voice runtime initialization failed: {exc}"

        # Anti-spoofing detector (AASIST). Failure is non-fatal: the heuristic
        # fallback provides an explicitly labeled, weaker analysis.
        try:
            detector = get_antispoof_detector()
            detector.load()
            self.status.antispoof_initialized = detector.is_loaded
            if detector.is_loaded:
                self.status.antispoof_model_name = f"aasist_{detector.variant.lower()}"
            self.status.antispoof_error = detector.error
        except AntispoofModelUnavailableError as exc:
            self.status.antispoof_initialized = False
            self.status.antispoof_error = exc.args[0] if exc.args else str(exc)
        except Exception as exc:
            self.status.antispoof_initialized = False
            self.status.antispoof_error = f"Anti-spoofing init failed: {exc}"

        return self.status

    def extract(self, voice_bytes: bytes) -> Tuple[np.ndarray, AudioQualityMetrics]:
        """Parse WAV, validate biometric quality, and extract the normalized speaker embedding."""
        samples, sr, props = parse_wav_bytes(voice_bytes)
        embedding = self._embedder.extract(samples, sr)
        self.dimension = self._embedder.dimension
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

        # Speaker embedding is produced off the event loop with a hard timeout.
        try:
            embedding = await asyncio.wait_for(
                asyncio.to_thread(self._embedder.extract, samples, sr),
                timeout=settings.VOICE_INFERENCE_TIMEOUT,
            )
            self.dimension = self._embedder.dimension
        except asyncio.TimeoutError:
            return VoiceResult(
                status=ModalityStatus.TIMEOUT,
                speech_detected=props.speech_ratio > 0.25,
                quality=AudioQualityMetrics(
                    duration_seconds=props.duration_seconds,
                    speech_ratio=props.speech_ratio,
                    snr_db=props.snr_db,
                ),
                reason_codes=["MODEL_TIMEOUT"],
            )
        except SpeakerModelUnavailableError as exc:
            return VoiceResult(
                status=ModalityStatus.MODEL_UNAVAILABLE,
                speech_detected=props.speech_ratio > 0.25,
                quality=AudioQualityMetrics(
                    duration_seconds=props.duration_seconds,
                    speech_ratio=props.speech_ratio,
                    snr_db=props.snr_db,
                ),
                reason_codes=["VOICE_MODEL_UNAVAILABLE", f"VOICE_MODEL_ERROR:{exc}"],
            )
        except VoiceProcessingError as exc:
            return VoiceResult(
                status=ModalityStatus.ERROR,
                speech_detected=props.speech_ratio > 0.25,
                reason_codes=[f"VOICE_INFERENCE_ERROR:{str(exc)}"],
            )

        quality = AudioQualityMetrics(
            duration_seconds=props.duration_seconds,
            speech_ratio=props.speech_ratio,
            snr_db=props.snr_db,
        )

        # Anti-spoof check (independent of identity evidence).
        # Runs off the event loop because AASIST inference may block.
        antispoof_res = await asyncio.to_thread(
            evaluate_audio_antispoof,
            samples,
            sr,
            min_confidence=settings.VOICE_LIVENESS_MIN_CONFIDENCE,
        )

        reason_codes = []
        similarity = None
        is_match = False

        if antispoof_res.is_synthetic_speech:
            reason_codes.append("AUDIO_SPOOF_RISK")
            reason_codes.append("VOICE_SYNTHETIC_SPEECH_DETECTED")
        else:
            reason_codes.append("VOICE_ANTISPOOF_BONA_FIDE")

        # Identity matching against the database enrolled voice template
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
                if stored_vec.shape[0] != embedding.shape[0]:
                    reason_codes.append("VOICE_TEMPLATE_INCOMPATIBLE")
                else:
                    similarity = compute_voice_similarity(embedding, stored_vec)
                    if (
                        similarity >= settings.VOICE_MATCH_THRESHOLD
                        and not antispoof_res.is_synthetic_speech
                    ):
                        is_match = True
                        reason_codes.append("VOICE_IDENTITY_MATCH")
                    else:
                        reason_codes.append("VOICE_IDENTITY_MISMATCH")
            else:
                reason_codes.append("VOICE_TEMPLATE_NOT_ENROLLED")
        elif claimed_subject_id and not session:
            reason_codes.append("VOICE_DATABASE_SESSION_MISSING")
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

    async def evaluate_antispoof(self, voice_bytes: bytes) -> dict:
        """Standalone voice presentation attack and synthetic speech evaluation."""
        samples, sr, props = parse_wav_bytes(voice_bytes)
        result = await asyncio.to_thread(
            evaluate_audio_antispoof,
            samples,
            sr,
            min_confidence=settings.VOICE_LIVENESS_MIN_CONFIDENCE,
        )
        return {
            "status": "available",
            "speech_detected": props.speech_ratio > 0.25,
            "duration_seconds": props.duration_seconds,
            "genuine_probability": result.genuine_probability,
            "spoof_probability": result.spoof_probability,
            "is_synthetic_speech": result.is_synthetic_speech,
            "state": result.state,
            "model_name": result.model_name,
            "details": result.details,
        }


voice_runtime = VoiceRuntime()
