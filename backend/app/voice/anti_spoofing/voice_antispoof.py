"""Voice presentation attack and synthetic speech detection.

Analyzes acoustic high-frequency distribution, spectral flatness,
harmonic structure, and temporal modulation to distinguish genuine live speech
from synthetic voice cloning, text-to-speech (TTS), and replay attacks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy import signal


@dataclass(frozen=True)
class VoiceAntispoofResult:
    genuine_probability: float  # 1.0 = live human speech, 0.0 = synthetic clone/replay
    spoof_probability: float  # 1.0 = synthetic / spoof
    is_synthetic_speech: bool
    state: str  # "bona_fide", "synthetic", "uncertain"
    model_name: str
    details: dict


def evaluate_audio_antispoof(
    samples: np.ndarray,
    sample_rate: int,
    min_confidence: float = 0.80,
) -> VoiceAntispoofResult:
    """Analyze acoustic characteristics for synthetic voice and replay markers."""
    if len(samples) == 0:
        return VoiceAntispoofResult(
            genuine_probability=0.0,
            spoof_probability=1.0,
            is_synthetic_speech=True,
            state="synthetic",
            model_name="acoustic_spectral_antispoof",
            details={"error": "empty_signal"},
        )

    # 1. High-frequency boundary inspection (synthetic TTS often has unnatural cutoffs > 7.5kHz or flat noise)
    fft_vals = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)

    # High frequency energy ratio (> 4kHz vs full)
    hf_mask = freqs > 4000.0
    lf_mask = (freqs >= 100.0) & (freqs <= 4000.0)
    hf_energy = np.sum(fft_vals[hf_mask] ** 2) + 1e-9
    lf_energy = np.sum(fft_vals[lf_mask] ** 2) + 1e-9
    hf_ratio = float(hf_energy / (hf_energy + lf_energy))

    # 2. Spectral Flatness (Wiener entropy): synthetic vocoders or replay artifacts have high flatness
    geom_mean = np.exp(np.mean(np.log(np.maximum(fft_vals[lf_mask], 1e-8))))
    arith_mean = np.mean(fft_vals[lf_mask]) + 1e-9
    spectral_flatness = float(geom_mean / arith_mean)

    # 3. Dynamic range / energy envelope variance
    frame_len = int(sample_rate * 0.03)  # 30ms frames
    if frame_len > 0 and len(samples) >= frame_len:
        num_frames = len(samples) // frame_len
        frame_energies = np.mean(
            samples[: num_frames * frame_len].reshape(num_frames, frame_len) ** 2,
            axis=1,
        )
        energy_std = float(np.std(frame_energies) / (np.mean(frame_energies) + 1e-7))
    else:
        energy_std = 1.0

    # Human live speech has natural harmonic peaks (lower flatness < 0.25), balanced HF ratio (0.05 - 0.35),
    # and dynamic pitch/energy modulation (energy_std > 0.5)
    flatness_penalty = max(0.0, min(1.0, (spectral_flatness - 0.15) * 3.0))
    hf_penalty = max(0.0, min(1.0, abs(hf_ratio - 0.20) * 4.0)) if hf_ratio > 0.45 or hf_ratio < 0.02 else 0.0
    modulation_score = min(1.0, max(0.0, energy_std * 0.6))

    # Genuine score formulation
    base_genuine = 0.95 - (flatness_penalty * 0.45 + hf_penalty * 0.35)
    genuine_score = float(np.clip(base_genuine * (0.8 + 0.2 * modulation_score), 0.05, 0.99))
    spoof_score = float(round(1.0 - genuine_score, 4))
    genuine_score = float(round(genuine_score, 4))

    if genuine_score >= min_confidence:
        state = "bona_fide"
        is_synthetic = False
    elif genuine_score <= (min_confidence - 0.25) or spoof_score >= 0.50:
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
        model_name="acoustic_spectral_antispoof",
        details={
            "spectral_flatness": round(spectral_flatness, 4),
            "hf_energy_ratio": round(hf_ratio, 4),
            "modulation_std": round(energy_std, 4),
        },
    )

