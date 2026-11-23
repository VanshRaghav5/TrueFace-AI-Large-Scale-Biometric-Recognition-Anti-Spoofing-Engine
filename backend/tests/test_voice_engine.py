import io
import math
import wave

import numpy as np
import pytest

from backend.app.voice.speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    SpeakerModelUnavailableError,
    compute_voice_similarity,
    extract_acoustic_embedding,
    get_speaker_embedder,
    parse_wav_bytes,
)
from backend.app.voice.anti_spoofing.voice_antispoof import evaluate_audio_antispoof
from backend.app.voice.anti_spoofing.voice_antispoof import (
    AASISTDetector,
    AntispoofModelUnavailableError,
    get_antispoof_detector,
)


def generate_synth_wav(freq: float = 440.0, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Speech-like wave with fundamental frequency and harmonics
    sig = 0.6 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    # Amplitude modulation
    sig *= (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t))
    int16_samples = (sig * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(int16_samples.tobytes())
    return buf.getvalue()


def _model_ready() -> bool:
    """True when the SpeechBrain speaker model can be loaded (cached locally)."""
    try:
        get_speaker_embedder().load()
        return get_speaker_embedder().is_loaded
    except SpeakerModelUnavailableError:
        return False
    except Exception:
        return False


needs_model = pytest.mark.skipif(
    not _model_ready(), reason="SpeechBrain speaker model unavailable or not downloaded"
)


# --- Pure unit tests (no model required) -------------------------------

def test_parse_wav_bytes():
    wav_bytes = generate_synth_wav(440.0, 1.0, 16000)
    samples, sr, props = parse_wav_bytes(wav_bytes)
    assert sr == 16000
    assert len(samples) == 16000
    assert props.duration_seconds == 1.0
    assert props.speech_ratio > 0.0


def test_parse_wav_rejects_empty():
    with pytest.raises(InvalidAudioError):
        parse_wav_bytes(b"not a wav file")


def test_parse_wav_rejects_too_short():
    short_wav = generate_synth_wav(440.0, 0.2, 16000)
    with pytest.raises(AudioQualityError):
        parse_wav_bytes(short_wav)


def test_compute_voice_similarity_math():
    # Identical unit vectors -> cosine 1.0
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert math.isclose(compute_voice_similarity(a, b), 1.0, rel_tol=1e-6)

    # Orthogonal vectors -> cosine 0.0 (clipped to [0, 1])
    c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    assert math.isclose(compute_voice_similarity(a, c), 0.0, abs_tol=1e-6)

    # Opposite vectors -> cosine -1, clipped to 0.0
    d = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    assert math.isclose(compute_voice_similarity(a, d), 0.0, abs_tol=1e-6)

    # Dimension mismatch is a non-match (0.0), never a crash
    e = np.array([1.0, 0.0], dtype=np.float32)
    assert compute_voice_similarity(a, e) == 0.0


def test_audio_antispoof_evaluation():
    wav_bytes = generate_synth_wav(220.0, 1.0, 16000)
    samples, sr, _ = parse_wav_bytes(wav_bytes)
    res = evaluate_audio_antispoof(samples, sr, min_confidence=0.80)
    assert 0.0 <= res.genuine_probability <= 1.0
    assert 0.0 <= res.spoof_probability <= 1.0
    assert res.state in ("bona_fide", "synthetic", "uncertain")
    # Model name must be explicit — never empty or silent.
    assert res.model_name in ("aasist_aasist", "aasist_aasist-l", "acoustic_spectral_fallback")
    assert res.genuine_probability + res.spoof_probability == pytest.approx(1.0, abs=0.01)


def _antispoof_model_ready() -> bool:
    """True when the AASIST weights can be loaded from disk."""
    try:
        get_antispoof_detector().load()
        return get_antispoof_detector().is_loaded
    except AntispoofModelUnavailableError:
        return False
    except Exception:
        return False


needs_antispoof_model = pytest.mark.skipif(
    not _antispoof_model_ready(), reason="AASIST weights unavailable"
)


@needs_antispoof_model
def test_aasist_detects_synthetic_audio():
    """AASIST should classify a pure sine wave as synthetic (spoof)."""
    sr = 16000
    t = np.linspace(0, 4, sr * 4, endpoint=False)
    sine = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    detector = get_antispoof_detector()
    res = detector.detect(sine, sr)
    assert res.model_name.startswith("aasist")
    assert res.state == "synthetic"
    assert res.is_synthetic_speech is True
    assert res.spoof_probability > 0.5
    assert "bonafide_logit" in res.details
    assert "spoof_logit" in res.details
    assert res.details["num_samples"] == 64600


@needs_antispoof_model
def test_aasist_handles_short_audio():
    """Audio shorter than 64600 samples must be padded (tiled), not rejected."""
    sr = 16000
    t = np.linspace(0, 0.5, sr // 2, endpoint=False)
    short = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    detector = get_antispoof_detector()
    res = detector.detect(short, sr)
    assert res.details["num_samples"] == 64600
    assert res.state in ("bona_fide", "synthetic", "uncertain")


@needs_antispoof_model
def test_aasist_empty_signal():
    """Empty signal must produce a synthetic result without crashing."""
    detector = get_antispoof_detector()
    res = detector.detect(np.array([], dtype=np.float32), 16000)
    assert res.state == "synthetic"
    assert res.is_synthetic_speech is True
    assert res.details.get("error") == "empty_signal"


@needs_antispoof_model
def test_aasist_resamples_nonstandard_rate():
    """Audio at 8 kHz must be resampled to 16 kHz before inference."""
    sr = 8000
    t = np.linspace(0, 4, sr * 4, endpoint=False)
    sine = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    detector = get_antispoof_detector()
    res = detector.detect(sine, sr)
    assert res.details["num_samples"] == 64600


def test_antispoof_result_model_name_explicit():
    """Regardless of engine, model_name must identify which ran (no silent path)."""
    sr = 16000
    t = np.linspace(0, 2, sr * 2, endpoint=False)
    sine = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    res = evaluate_audio_antispoof(sine, sr)
    assert res.model_name in ("aasist_aasist", "aasist_aasist-l", "acoustic_spectral_fallback")


# --- Integration tests (require the downloaded SpeechBrain model) -----

@needs_model
def test_speaker_embedding_shape_and_norm():
    wav_bytes = generate_synth_wav(220.0, 1.5, 16000)
    samples, sr, _ = parse_wav_bytes(wav_bytes)
    vec = extract_acoustic_embedding(samples, sr)
    assert vec.ndim == 1
    assert vec.shape[0] == get_speaker_embedder().dimension
    assert math.isclose(float(np.linalg.norm(vec)), 1.0, rel_tol=1e-4)


@needs_model
def test_speaker_embedding_deterministic():
    wav_bytes = generate_synth_wav(330.0, 1.5, 16000)
    samples, sr, _ = parse_wav_bytes(wav_bytes)
    v1 = extract_acoustic_embedding(samples, sr)
    v2 = extract_acoustic_embedding(samples, sr)
    # Deterministic re-encoding of the same signal is an exact self-match.
    assert math.isclose(compute_voice_similarity(v1, v2), 1.0, rel_tol=1e-5)
