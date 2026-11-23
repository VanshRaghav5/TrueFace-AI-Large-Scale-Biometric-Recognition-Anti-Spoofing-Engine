"""Voice presentation attack and synthetic speech detection.

Primary engine: AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal
graph attention networks), pretrained on ASVspoof 2019 LA. The model ingests a
raw waveform, classifies it as bona-fide vs. spoof, and outputs a genuine-speech
probability. The pretrained weights are bundled with the project.

Fallback engine: when the AASIST weights are unavailable (torch missing,
file not found), an acoustic-spectral heuristic provides a weaker but explicit
analysis. The ``model_name`` field on every result identifies which engine
produced it so callers never get silent degradation.
"""

from __future__ import annotations

import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy import signal as scipy_signal


class AntispoofModelUnavailableError(Exception):
    """Raised when the AASIST anti-spoofing model could not be loaded."""


@dataclass(frozen=True)
class VoiceAntispoofResult:
    genuine_probability: float  # 1.0 = live human speech, 0.0 = synthetic/replay
    spoof_probability: float     # 1.0 = synthetic/spoof
    is_synthetic_speech: bool
    state: str                   # "bona_fide", "synthetic", "uncertain", "model_unavailable"
    model_name: str
    details: dict


# ---------------------------------------------------------------------------
# AASIST detector
# ---------------------------------------------------------------------------

class AASISTDetector:
    """Owns one reusable AASIST anti-spoofing model.

    Loading is decoupled from inference: call :meth:`load` at startup (or rely
    on lazy first-call load), then :meth:`detect` for each request.
    """

    MODEL_NAME = "aasist"
    MODEL_VERSION = "v1"
    TARGET_SAMPLE_RATE = 16_000
    NB_SAMP = 64_600  # ~4 s at 16 kHz — matches pretrained training config

    def __init__(self, weights_path: str, device: str = "cpu",
                 threshold: float = 0.5) -> None:
        self.weights_path = weights_path
        self.device = device
        self.threshold = threshold
        self._lock = threading.Lock()
        self._model = None
        self._variant: Optional[str] = None
        self._error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def variant(self) -> str:
        return self._variant or "AASIST"

    def _resolve_weights_path(self) -> Path:
        from ...core.config import PROJECT_ROOT

        path = Path(self.weights_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    def _detect_variant(self, path: Path) -> str:
        """Infer the model variant from the file name (AASIST vs AASIST-L)."""
        name = path.stem.upper()
        if "L" in name and "AASIST" in name:
            return "AASIST-L"
        return "AASIST"

    def load(self) -> None:
        """Instantiate the AASIST architecture and load pretrained weights.

        Thread-safe and idempotent. Raises
        :class:`AntispoofModelUnavailableError` when torch or the weights file
        is missing.
        """
        with self._lock:
            if self._model is not None:
                return
            from ...core.config import settings

            if not settings.VOICE_ANTISPOOF_ENABLED:
                self._error = "Voice anti-spoofing is disabled by configuration"
                raise AntispoofModelUnavailableError(self._error)
            try:
                import torch
            except ImportError as exc:
                self._error = f"PyTorch is not installed: {exc.name or exc}"
                raise AntispoofModelUnavailableError(self._error) from exc

            weights_path = self._resolve_weights_path()
            if not weights_path.is_file():
                self._error = f"AASIST weights not found: {weights_path}"
                raise AntispoofModelUnavailableError(self._error)

            try:
                from .aasist_model import AASIST_CONFIGS, Model

                self._variant = self._detect_variant(weights_path)
                config = AASIST_CONFIGS.get(self._variant, AASIST_CONFIGS["AASIST"])
                model = Model(config)
                state_dict = torch.load(str(weights_path), map_location=self.device)
                model.load_state_dict(state_dict)
                model.to(self.device)
                model.eval()
                self._model = model
                self._error = None
            except AntispoofModelUnavailableError:
                raise
            except Exception as exc:
                self._model = None
                self._error = f"Failed to load AASIST weights '{weights_path}': {exc}"
                raise AntispoofModelUnavailableError(self._error) from exc

    def _require_model(self):
        if self._model is None:
            self.load()
        if self._model is None:
            raise AntispoofModelUnavailableError(self._error or "AASIST model is unavailable")
        return self._model

    def detect(self, samples: np.ndarray, sample_rate: int) -> VoiceAntispoofResult:
        """Run AASIST inference on a 1-D float32 waveform.

        Returns a :class:`VoiceAntispoofResult` with softmax probabilities
        and the bonafide/spoof logits in ``details``.
        """
        if len(samples) == 0:
            return VoiceAntispoofResult(
                genuine_probability=0.0,
                spoof_probability=1.0,
                is_synthetic_speech=True,
                state="synthetic",
                model_name=self.MODEL_NAME,
                details={"error": "empty_signal"},
            )

        import torch
        import torch.nn.functional as F

        # Resample to 16 kHz if needed
        if sample_rate != self.TARGET_SAMPLE_RATE:
            num_target = int(len(samples) * self.TARGET_SAMPLE_RATE / sample_rate)
            if num_target <= 0:
                return VoiceAntispoofResult(
                    genuine_probability=0.0, spoof_probability=1.0,
                    is_synthetic_speech=True, state="synthetic",
                    model_name=self.MODEL_NAME,
                    details={"error": "audio_too_short_to_resample"},
                )
            samples = scipy_signal.resample(samples, num_target)

        from .aasist_model import pad_audio

        padded = pad_audio(np.ascontiguousarray(samples, dtype=np.float32), self.NB_SAMP)

        model = self._require_model()
        x = torch.from_numpy(padded).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            _, output = model(x, Freq_aug=False)

        logits = output.squeeze(0).cpu().numpy()
        bonafide_logit = float(logits[1])
        spoof_logit = float(logits[0])

        probs = F.softmax(output, dim=1).squeeze(0).cpu().numpy()
        bonafide_prob = float(probs[1])
        spoof_prob = float(probs[0])

        bonafide_prob = round(bonafide_prob, 4)
        spoof_prob = round(spoof_prob, 4)

        # Classification: only block on confident spoof detection. The "uncertain"
        # zone (between spoof_floor and threshold) does NOT set is_synthetic, so
        # it does not block the identity match. This avoids false rejections
        # caused by domain mismatch between training data (ASVspoof 2019 LA
        # studio recordings) and browser microphone recordings.
        spoof_floor = 0.15  # bonafide below this = confident spoof
        if bonafide_prob >= self.threshold:
            state = "bona_fide"
            is_synthetic = False
        elif bonafide_prob < spoof_floor:
            state = "synthetic"
            is_synthetic = True
        else:
            state = "uncertain"
            is_synthetic = False

        return VoiceAntispoofResult(
            genuine_probability=bonafide_prob,
            spoof_probability=spoof_prob,
            is_synthetic_speech=is_synthetic,
            state=state,
            model_name=f"aasist_{self.variant.lower()}",
            details={
                "bonafide_logit": round(bonafide_logit, 4),
                "spoof_logit": round(spoof_logit, 4),
                "bonafide_prob": bonafide_prob,
                "spoof_prob": spoof_prob,
                "num_samples": int(len(padded)),
                "model": f"aasist_{self.variant.lower()}",
                "threshold": self.threshold,
            },
        )


_detector: Optional[AASISTDetector] = None
_detector_lock = threading.Lock()


def get_antispoof_detector() -> AASISTDetector:
    """Return the process-wide :class:`AASISTDetector` singleton."""
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                from ...core.config import settings

                _detector = AASISTDetector(
                    weights_path=settings.VOICE_ANTISPOOF_MODEL_PATH,
                    device=settings.VOICE_ANTISPOOF_DEVICE,
                    threshold=settings.VOICE_ANTISPOOF_THRESHOLD,
                )
    return _detector


# ---------------------------------------------------------------------------
# Heuristic fallback (explicit, never silent)
# ---------------------------------------------------------------------------

def _heuristic_antispoof(
    samples: np.ndarray,
    sample_rate: int,
    min_confidence: float = 0.80,
) -> VoiceAntispoofResult:
    """Acoustic-spectral heuristic used only when AASIST is unavailable.

    Analyzes high-frequency distribution, spectral flatness, harmonic
    structure, and temporal modulation. Weaker than AASIST but provides an
    explicit, labeled fallback instead of silently passing audio through.
    """
    if len(samples) == 0:
        return VoiceAntispoofResult(
            genuine_probability=0.0,
            spoof_probability=1.0,
            is_synthetic_speech=True,
            state="synthetic",
            model_name="acoustic_spectral_fallback",
            details={"error": "empty_signal"},
        )

    fft_vals = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)

    hf_mask = freqs > 4000.0
    lf_mask = (freqs >= 100.0) & (freqs <= 4000.0)
    hf_energy = np.sum(fft_vals[hf_mask] ** 2) + 1e-9
    lf_energy = np.sum(fft_vals[lf_mask] ** 2) + 1e-9
    hf_ratio = float(hf_energy / (hf_energy + lf_energy))

    geom_mean = np.exp(np.mean(np.log(np.maximum(fft_vals[lf_mask], 1e-8))))
    arith_mean = np.mean(fft_vals[lf_mask]) + 1e-9
    spectral_flatness = float(geom_mean / arith_mean)

    frame_len = int(sample_rate * 0.03)
    if frame_len > 0 and len(samples) >= frame_len:
        num_frames = len(samples) // frame_len
        frame_energies = np.mean(
            samples[: num_frames * frame_len].reshape(num_frames, frame_len) ** 2,
            axis=1,
        )
        energy_std = float(np.std(frame_energies) / (np.mean(frame_energies) + 1e-7))
    else:
        energy_std = 1.0

    flatness_penalty = max(0.0, min(1.0, (spectral_flatness - 0.15) * 3.0))
    hf_penalty = max(0.0, min(1.0, abs(hf_ratio - 0.20) * 4.0)) if hf_ratio > 0.45 or hf_ratio < 0.02 else 0.0
    modulation_score = min(1.0, max(0.0, energy_std * 0.6))

    base_genuine = 0.95 - (flatness_penalty * 0.45 + hf_penalty * 0.35)
    genuine_score = float(np.clip(base_genuine * (0.8 + 0.2 * modulation_score), 0.05, 0.99))
    spoof_score = float(round(1.0 - genuine_score, 4))
    genuine_score = float(round(genuine_score, 4))

    # Same classification logic as AASIST: only block on confident spoof.
    spoof_floor = 0.15
    if genuine_score >= min_confidence:
        state = "bona_fide"
        is_synthetic = False
    elif genuine_score < spoof_floor:
        state = "synthetic"
        is_synthetic = True
    else:
        state = "uncertain"
        is_synthetic = False

    return VoiceAntispoofResult(
        genuine_probability=genuine_score,
        spoof_probability=spoof_score,
        is_synthetic_speech=is_synthetic,
        state=state,
        model_name="acoustic_spectral_fallback",
        details={
            "spectral_flatness": round(spectral_flatness, 4),
            "hf_energy_ratio": round(hf_ratio, 4),
            "modulation_std": round(energy_std, 4),
            "fallback_reason": "aasist_model_unavailable",
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_audio_antispoof(
    samples: np.ndarray,
    sample_rate: int,
    min_confidence: float = 0.80,
) -> VoiceAntispoofResult:
    """Analyze audio for synthetic voice and replay attacks.

    Uses AASIST when the model is loaded. Falls back to the acoustic-spectral
    heuristic when it is not — the result's ``model_name`` always indicates
    which engine ran so callers can detect degradation explicitly.
    """
    detector = get_antispoof_detector()
    if detector.is_loaded:
        return detector.detect(samples, sample_rate)
    # AASIST not loaded — try a lazy load once, then fall back.
    try:
        detector.load()
        if detector.is_loaded:
            return detector.detect(samples, sample_rate)
    except AntispoofModelUnavailableError:
        pass
    return _heuristic_antispoof(samples, sample_rate, min_confidence)
