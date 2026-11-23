"""Speaker verification engine for TrueFaceAI.

Extracts normalized acoustic spectral embeddings from audio samples
and calculates cosine similarity against enrolled voice templates.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import numpy as np
from scipy import signal
from scipy.fft import rfft


class VoiceProcessingError(Exception):
    """Base error for voice processing failures."""


class InvalidAudioError(VoiceProcessingError):
    """Raised when audio data is malformed or empty."""


class AudioQualityError(VoiceProcessingError):
    """Raised when audio quality does not meet minimum biometric standards."""


@dataclass(frozen=True)
class AudioProperties:
    sample_rate: int
    num_channels: int
    duration_seconds: float
    num_frames: int
    speech_ratio: float
    snr_db: float


def parse_wav_bytes(audio_bytes: bytes) -> Tuple[np.ndarray, int, AudioProperties]:
    """Parse WAV byte stream into float32 mono waveform normalized to [-1.0, 1.0]."""
    if not audio_bytes or len(audio_bytes) < 44:
        raise InvalidAudioError("Audio payload is empty or too short for a valid WAV header")

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            n_frames = wav.getnframes()
            raw_frames = wav.readframes(n_frames)
    except Exception as exc:
        raise InvalidAudioError(f"Failed to decode WAV audio: {exc}") from exc

    if sample_width not in (1, 2, 4):
        raise InvalidAudioError(f"Unsupported sample width: {sample_width} bytes")
    if sample_rate < 8000:
        raise AudioQualityError(f"Audio sample rate {sample_rate} Hz is too low for biometric verification")

    if sample_width == 1:
        samples = np.frombuffer(raw_frames, dtype=np.uint8).astype(np.float32) - 128.0
        samples /= 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        samples = np.frombuffer(raw_frames, dtype=np.int32).astype(np.float32) / 2147483648.0

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    duration = float(len(samples)) / float(sample_rate)
    if duration < 0.4:
        raise AudioQualityError(f"Audio duration {duration:.2f}s is too short (minimum 0.5s required)")

    # Voice activity detection & speech ratio
    frame_len = int(sample_rate * 0.025)  # 25ms
    if frame_len < 1:
        frame_len = 256
    num_blocks = len(samples) // frame_len
    if num_blocks > 0:
        blocks = samples[: num_blocks * frame_len].reshape(num_blocks, frame_len)
        energies = np.mean(blocks ** 2, axis=1)
        noise_floor = np.percentile(energies, 15) + 1e-9
        peak_energy = np.percentile(energies, 95) + 1e-9
        threshold = noise_floor * 3.0
        active_blocks = np.sum(energies > threshold)
        speech_ratio = float(active_blocks) / float(num_blocks)
        snr = float(10.0 * np.log10(max(1.0, peak_energy / noise_floor)))
    else:
        speech_ratio = 1.0
        snr = 20.0

    props = AudioProperties(
        sample_rate=sample_rate,
        num_channels=n_channels,
        duration_seconds=round(duration, 3),
        num_frames=n_frames,
        speech_ratio=round(min(1.0, max(0.0, speech_ratio)), 3),
        snr_db=round(snr, 2),
    )
    return samples, sample_rate, props


def extract_acoustic_embedding(samples: np.ndarray, sample_rate: int, dim: int = 128) -> np.ndarray:
    """Extract a 128-dimensional normalized acoustic filterbank embedding."""
    if len(samples) == 0:
        raise InvalidAudioError("Audio signal is empty")

    # Resample to 16kHz standard if necessary
    target_sr = 16000
    if sample_rate != target_sr:
        num_target = int(len(samples) * target_sr / sample_rate)
        if num_target > 0:
            samples = signal.resample(samples, num_target)
            sample_rate = target_sr

    frame_size = 512
    hop_size = 256
    window = np.hanning(frame_size)

    num_frames = max(1, (len(samples) - frame_size) // hop_size + 1)
    mel_filters = 32

    # Mel-scale filterbank construction
    low_freq = 100.0
    high_freq = sample_rate / 2.0
    mel_points = np.linspace(
        2595 * np.log10(1 + low_freq / 700.0),
        2595 * np.log10(1 + high_freq / 700.0),
        mel_filters + 2,
    )
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
    bin_points = np.floor((frame_size + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((mel_filters, frame_size // 2 + 1), dtype=np.float32)
    for m in range(1, mel_filters + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]
        for k in range(f_m_minus, f_m):
            if f_m > f_m_minus:
                fbank[m - 1, k] = (k - f_m_minus) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if f_m_plus > f_m:
                fbank[m - 1, k] = (f_m_plus - k) / (f_m_plus - f_m)

    energies = []
    for i in range(num_frames):
        start = i * hop_size
        block = samples[start : start + frame_size]
        if len(block) < frame_size:
            block = np.pad(block, (0, frame_size - len(block)))
        spectrum = np.abs(rfft(block * window)) ** 2
        filter_energies = np.dot(fbank, spectrum)
        filter_energies = np.log(np.maximum(filter_energies, 1e-8))
        energies.append(filter_energies)

    energies_arr = np.array(energies)  # (num_frames, 32)
    # Aggregate statistical moments: mean, std, skew/min, max -> 32 * 4 = 128-dim
    mean_vec = np.mean(energies_arr, axis=0)
    std_vec = np.std(energies_arr, axis=0)
    min_vec = np.min(energies_arr, axis=0)
    max_vec = np.max(energies_arr, axis=0)

    raw_embedding = np.concatenate([mean_vec, std_vec, min_vec, max_vec]).astype(np.float32)
    if len(raw_embedding) != dim:
        raw_embedding = np.resize(raw_embedding, dim)

    norm = float(np.linalg.norm(raw_embedding))
    if norm < 1e-8:
        raw_embedding = np.ones(dim, dtype=np.float32) / math.sqrt(dim)
    else:
        raw_embedding = raw_embedding / norm

    return raw_embedding.astype(np.float32)


def compute_voice_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two voice embeddings in [0.0, 1.0]."""
    u = np.asarray(vec1, dtype=np.float32).reshape(-1)
    v = np.asarray(vec2, dtype=np.float32).reshape(-1)
    if u.shape != v.shape or u.size == 0:
        return 0.0
    dot = float(np.dot(u, v))
    norm_u = float(np.linalg.norm(u))
    norm_v = float(np.linalg.norm(v))
    if norm_u < 1e-8 or norm_v < 1e-8:
        return 0.0
    cos_sim = dot / (norm_u * norm_v)
    # Scale from [-1, 1] to normalized [0, 1]
    return float(np.clip(cos_sim, 0.0, 1.0))

