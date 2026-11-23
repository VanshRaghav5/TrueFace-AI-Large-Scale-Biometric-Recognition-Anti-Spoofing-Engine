import io
import math
import struct
import wave
import numpy as np
import pytest

from backend.app.voice.speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    compute_voice_similarity,
    extract_acoustic_embedding,
    parse_wav_bytes,
)
from backend.app.voice.anti_spoofing.voice_antispoof import evaluate_audio_antispoof


def generate_synth_wav(freq: float = 440.0, duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Speech-like wave with fundamental frequency and harmonics
    signal = 0.6 * np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    # Amplitude modulation
    signal *= (0.5 + 0.5 * np.sin(2 * np.pi * 3.0 * t))
    int16_samples = (signal * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(int16_samples.tobytes())
    return buf.getvalue()


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


def test_extract_acoustic_embedding_normalized():
    samples = np.sin(np.linspace(0, 100, 16000)).astype(np.float32)
    vec = extract_acoustic_embedding(samples, 16000, dim=128)
    assert vec.shape == (128,)
    assert math.isclose(float(np.linalg.norm(vec)), 1.0, rel_tol=1e-4)


def test_voice_similarity_identical_and_different():
    wav1 = generate_synth_wav(300.0, 1.0, 16000)
    wav2 = generate_synth_wav(300.0, 1.0, 16000)
    wav3 = generate_synth_wav(800.0, 1.0, 16000)

    s1, sr1, _ = parse_wav_bytes(wav1)
    s2, sr2, _ = parse_wav_bytes(wav2)
    s3, sr3, _ = parse_wav_bytes(wav3)

    v1 = extract_acoustic_embedding(s1, sr1)
    v2 = extract_acoustic_embedding(s2, sr2)
    v3 = extract_acoustic_embedding(s3, sr3)

    sim_same = compute_voice_similarity(v1, v2)
    sim_diff = compute_voice_similarity(v1, v3)

    assert sim_same > 0.95
    assert sim_same > sim_diff


def test_audio_antispoof_evaluation():
    wav_bytes = generate_synth_wav(220.0, 1.0, 16000)
    samples, sr, _ = parse_wav_bytes(wav_bytes)
    res = evaluate_audio_antispoof(samples, sr, min_confidence=0.80)
    assert 0.0 <= res.genuine_probability <= 1.0
    assert 0.0 <= res.spoof_probability <= 1.0
    assert res.state in ("bona_fide", "synthetic", "uncertain")

