#!/usr/bin/env python
"""Comprehensive AASIST voice anti-spoofing pipeline test.

Tests the full integration: model loading, synthetic audio detection, fallback
heuristic, public API dispatch, edge cases, and AASIST-L variant.

Run from the project root:
    python scripts/test_antispoof_pipeline.py
"""

from __future__ import annotations

import io
import os
import sys
import time
import wave
from pathlib import Path

import numpy as np

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def make_wav_bytes(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Encode a float32 waveform as 16-bit PCM WAV bytes."""
    int16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(int16.tobytes())
    return buf.getvalue()


def banner(text: str) -> None:
    print(f"\n{'=' * 70}\n  {text}\n{'=' * 70}")


def ok(label: str, detail: str = "") -> None:
    print(f"  [OK] {label}" + (f"  {detail}" if detail else ""))


def fail(label: str, detail: str = "") -> None:
    print(f"  [FAIL] {label}" + (f"  {detail}" if detail else ""))


def warn(label: str, detail: str = "") -> None:
    print(f"  [WARN] {label}" + (f"  {detail}" if detail else ""))


def main() -> int:
    from backend.app.voice.anti_spoofing.voice_antispoof import (
        AASISTDetector,
        AntispoofModelUnavailableError,
        evaluate_audio_antispoof,
        get_antispoof_detector,
    )
    from backend.app.voice.anti_spoofing.aasist_model import AASIST_CONFIGS
    from backend.app.core.config import settings

    failures = 0
    sr = 16000

    banner("STEP 1: AASIST Model Loading")
    detector = get_antispoof_detector()
    t0 = time.time()
    try:
        detector.load()
        t1 = time.time()
    except AntispoofModelUnavailableError as exc:
        t1 = time.time()
        fail("AASIST model load", str(exc))
        failures += 1
        # Fall through to fallback tests
    if detector.is_loaded:
        ok("AASIST loaded", f"variant={detector.variant}, time={t1-t0:.2f}s")
    else:
        warn("AASIST not loaded", f"error={detector.error}")

    banner("STEP 2: Synthetic Audio Detection (AASIST)")
    if detector.is_loaded:
        # Pure sine wave — definitely synthetic
        t = np.linspace(0, 4, sr * 4, endpoint=False)
        sine = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        r = detector.detect(sine, sr)
        if r.state == "synthetic" and r.spoof_probability > 0.5:
            ok("Pure sine -> synthetic",
               f"genuine={r.genuine_probability}, spoof={r.spoof_probability}")
        else:
            fail("Pure sine -> synthetic",
                 f"state={r.state}, spoof={r.spoof_probability}")
            failures += 1

        # White noise — synthetic
        noise = (np.random.randn(sr * 4) * 0.1).astype(np.float32)
        r = detector.detect(noise, sr)
        if r.state == "synthetic":
            ok("White noise -> synthetic",
               f"genuine={r.genuine_probability}, spoof={r.spoof_probability}")
        else:
            fail("White noise -> synthetic", f"state={r.state}")
            failures += 1

        # Harmonic signal — synthetic (not real speech)
        sig = (0.6 * np.sin(2 * np.pi * 150 * t) +
               0.3 * np.sin(2 * np.pi * 300 * t) +
               0.15 * np.sin(2 * np.pi * 450 * t))
        sig *= (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t))
        r = detector.detect(sig.astype(np.float32), sr)
        if r.state == "synthetic":
            ok("Harmonic signal -> synthetic",
               f"genuine={r.genuine_probability}, spoof={r.spoof_probability}")
        else:
            fail("Harmonic signal -> synthetic", f"state={r.state}")
            failures += 1

        # Check details contain model-specific fields
        if "bonafide_logit" in r.details and "spoof_logit" in r.details:
            ok("Details include logits",
               f"bonafide_logit={r.details['bonafide_logit']}, "
               f"spoof_logit={r.details['spoof_logit']}")
        else:
            fail("Details missing logits", str(r.details))
            failures += 1
    else:
        warn("Skipping AASIST detection tests (model not loaded)")

    banner("STEP 3: Edge Cases")
    if detector.is_loaded:
        # Empty signal
        r = detector.detect(np.array([], dtype=np.float32), sr)
        if r.state == "synthetic" and r.details.get("error") == "empty_signal":
            ok("Empty signal -> synthetic with error flag")
        else:
            fail("Empty signal", f"state={r.state}")
            failures += 1

        # Short audio (0.5s) — should be padded to 64600
        t_short = np.linspace(0, 0.5, sr // 2, endpoint=False)
        short = (0.5 * np.sin(2 * np.pi * 200 * t_short)).astype(np.float32)
        r = detector.detect(short, sr)
        if r.details["num_samples"] == 64600:
            ok("Short audio padded to 64600 samples")
        else:
            fail("Short audio padding", f"num_samples={r.details['num_samples']}")
            failures += 1

        # Non-standard sample rate (8 kHz) — should be resampled
        sr_low = 8000
        t_low = np.linspace(0, 4, sr_low * 4, endpoint=False)
        sine_low = (0.5 * np.sin(2 * np.pi * 220 * t_low)).astype(np.float32)
        r = detector.detect(sine_low, sr_low)
        if r.details["num_samples"] == 64600:
            ok("8 kHz audio resampled to 16 kHz, padded to 64600")
        else:
            fail("Non-standard rate", f"num_samples={r.details['num_samples']}")
            failures += 1
    else:
        warn("Skipping edge case tests (model not loaded)")

    banner("STEP 4: Public API Dispatch")
    sine = (0.5 * np.sin(2 * np.pi * 220 * np.linspace(0, 4, sr * 4, endpoint=False))).astype(np.float32)
    r = evaluate_audio_antispoof(sine, sr, min_confidence=0.80)
    if r.model_name.startswith("aasist"):
        ok(f"evaluate_audio_antispoof -> AASIST (model_name={r.model_name})")
    elif r.model_name == "acoustic_spectral_fallback":
        warn("evaluate_audio_antispoof -> heuristic fallback",
             f"model_name={r.model_name}")
    else:
        fail("Unexpected model_name", r.model_name)
        failures += 1
    # genuine + spoof should sum to ~1.0
    total = r.genuine_probability + r.spoof_probability
    if abs(total - 1.0) < 0.02:
        ok("Probabilities sum to ~1.0", f"sum={total:.4f}")
    else:
        fail("Probabilities don't sum to 1.0", f"sum={total:.4f}")
        failures += 1

    banner("STEP 5: Fallback Heuristic (simulated unavailability)")
    # Test the heuristic directly
    from backend.app.voice.anti_spoofing.voice_antispoof import _heuristic_antispoof
    r_fb = _heuristic_antispoof(sine, sr, min_confidence=0.80)
    if r_fb.model_name == "acoustic_spectral_fallback":
        ok("Heuristic fallback labeled correctly",
           f"model_name={r_fb.model_name}, state={r_fb.state}")
    else:
        fail("Heuristic fallback label", r_fb.model_name)
        failures += 1
    if r_fb.details.get("fallback_reason") == "aasist_model_unavailable":
        ok("Fallback reason explicitly recorded in details")
    else:
        fail("Fallback reason missing", str(r_fb.details))
        failures += 1

    banner("STEP 6: AASIST-L Variant (if weights available)")
    aasist_l_path = PROJECT_ROOT / "models" / "models" / "anti_spoofing" / "AASIST-L.pth"
    aasist_l_path = PROJECT_ROOT / "models" / "voice" / "anti_spoofing" / "AASIST-L.pth"
    if aasist_l_path.is_file():
        try:
            detector_l = AASISTDetector(
                weights_path=str(aasist_l_path),
                device="cpu",
                threshold=0.5,
            )
            detector_l.load()
            if detector_l.is_loaded and detector_l.variant == "AASIST-L":
                ok("AASIST-L loaded", f"variant={detector_l.variant}")
                r_l = detector_l.detect(sine, sr)
                if r_l.model_name == "aasist_aasist-l":
                    ok("AASIST-L model_name correct",
                       f"model_name={r_l.model_name}")
                else:
                    fail("AASIST-L model_name", r_l.model_name)
                    failures += 1
                if r_l.state == "synthetic":
                    ok("AASIST-L detects synthetic audio",
                       f"spoof={r_l.spoof_probability}")
                else:
                    fail("AASIST-L detection", f"state={r_l.state}")
                    failures += 1
            else:
                fail("AASIST-L load", f"variant={detector_l.variant}")
                failures += 1
        except Exception as exc:
            fail("AASIST-L load", str(exc))
            failures += 1
    else:
        warn("AASIST-L weights not found", str(aasist_l_path))

    banner("STEP 7: Config Verification")
    ok("VOICE_ANTISPOOF_ENABLED", str(settings.VOICE_ANTISPOOF_ENABLED))
    ok("VOICE_ANTISPOOF_MODEL_PATH", settings.VOICE_ANTISPOOF_MODEL_PATH)
    ok("VOICE_ANTISPOOF_DEVICE", settings.VOICE_ANTISPOOF_DEVICE)
    ok("VOICE_ANTISPOOF_THRESHOLD", str(settings.VOICE_ANTISPOOF_THRESHOLD))
    # Verify architecture configs
    if "AASIST" in AASIST_CONFIGS and "AASIST-L" in AASIST_CONFIGS:
        ok("Architecture configs defined for both variants")
    else:
        fail("Architecture configs missing")
        failures += 1

    banner("SUMMARY")
    if failures == 0:
        print("  All checks passed.")
    else:
        print(f"  {failures} check(s) FAILED.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
