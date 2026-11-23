"""Speaker verification engine for TrueFaceAI.

Wraps the SpeechBrain ECAPA-TDNN speaker encoder (pretrained on VoxCeleb) to
extract normalized speaker embeddings, and computes cosine similarity against
enrolled voice templates.

The model is loaded once (either eagerly at startup via ``initialize`` or
lazily on first inference) and reused for every request. Per-request inference
never triggers a reload. If the model cannot be loaded (e.g. the package is
missing or the weights cannot be fetched) the embedder reports an explicit
unavailable state instead of silently degrading.
"""

from __future__ import annotations

import io
import math
import os
import threading
import wave
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy import signal


class VoiceProcessingError(Exception):
    """Base error for voice processing failures."""


class InvalidAudioError(VoiceProcessingError):
    """Raised when audio data is malformed or empty."""


class AudioQualityError(VoiceProcessingError):
    """Raised when audio quality does not meet minimum biometric standards."""


class SpeakerModelUnavailableError(VoiceProcessingError):
    """Raised when the speaker encoder model could not be loaded."""


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


class SpeakerEmbedder:
    """Owns one reusable SpeechBrain ECAPA-TDNN speaker encoder.

    Loading is decoupled from inference: call :meth:`load` (or rely on the lazy
    first-call load) to materialize the model, then :meth:`extract` for each
    request. The model is downloaded from HuggingFace into ``savedir`` on first
    use and read from disk afterwards.
    """

    MODEL_NAME = "ecapa_tdnn_voxceleb"
    MODEL_VERSION = "v1"
    TARGET_SAMPLE_RATE = 16000

    def __init__(self, source: str, savedir: str, device: str = "cpu") -> None:
        self.source = source
        self.savedir = savedir
        self.device = device
        self._lock = threading.Lock()
        self._model = None
        self._dim: Optional[int] = None
        self._error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def dimension(self) -> int:
        return self._dim if self._dim is not None else 192

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def model_version(self) -> str:
        return self.MODEL_VERSION

    def _resolve_savedir(self):
        from pathlib import Path
        from ...core.config import PROJECT_ROOT

        path = Path(self.savedir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def load(self) -> None:
        """Download and instantiate the speaker model. Thread-safe and idempotent."""
        with self._lock:
            if self._model is not None:
                return
            from ...core.config import settings

            if not settings.VOICE_SPEAKER_ENABLED:
                self._error = "Speaker verification model is disabled by configuration"
                raise SpeakerModelUnavailableError(self._error)
            try:
                import torch  # noqa: F401  (ensures torch is importable early)
                from speechbrain.inference.speaker import SpeakerRecognition
                from speechbrain.utils.fetching import LocalStrategy
            except ImportError as exc:
                self._error = f"SpeechBrain is not installed: {exc.name or exc}"
                raise SpeakerModelUnavailableError(self._error) from exc

            # COPY avoids the Windows symlink privilege requirement (WinError 1314).
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            try:
                save_dir = self._resolve_savedir()
                self._model = SpeakerRecognition.from_hparams(
                    source=self.source,
                    savedir=str(save_dir),
                    run_opts={"device": self.device},
                    local_strategy=LocalStrategy.COPY,
                )
                self._error = None
            except Exception as exc:
                self._model = None
                self._error = f"Failed to load speaker model '{self.source}': {exc}"
                raise SpeakerModelUnavailableError(self._error) from exc

    def _require_model(self):
        if self._model is None:
            self.load()
        if self._model is None:
            raise SpeakerModelUnavailableError(self._error or "Speaker model is unavailable")
        return self._model

    def extract(self, samples: np.ndarray, sample_rate: int) -> np.ndarray:
        """Extract an L2-normalized speaker embedding from a 1D float32 waveform.

        Returns a 1-D float32 array. The dimension is determined by the loaded
        model (192 for ``spkrec-ecapa-voxceleb``).
        """
        if len(samples) == 0:
            raise InvalidAudioError("Audio signal is empty")

        import torch

        if sample_rate != self.TARGET_SAMPLE_RATE:
            num_target = int(len(samples) * self.TARGET_SAMPLE_RATE / sample_rate)
            if num_target <= 0:
                raise AudioQualityError("Audio is too short to resample")
            samples = signal.resample(samples, num_target)
            sample_rate = self.TARGET_SAMPLE_RATE

        model = self._require_model()
        wav = torch.from_numpy(np.ascontiguousarray(samples, dtype=np.float32)).unsqueeze(0)
        wav_lens = torch.tensor([1.0])
        with torch.no_grad():
            embedding = model.encode_batch(wav, wav_lens, normalize=False)
        vector = embedding.squeeze().detach().cpu().numpy().astype(np.float32).reshape(-1)

        self._dim = int(vector.shape[0])
        norm = float(np.linalg.norm(vector))
        if norm < 1e-8:
            raise VoiceProcessingError("Degenerate speaker embedding (zero norm)")
        return (vector / norm).astype(np.float32)


_embedder: Optional[SpeakerEmbedder] = None
_embedder_lock = threading.Lock()


def get_speaker_embedder() -> SpeakerEmbedder:
    """Return the process-wide :class:`SpeakerEmbedder` singleton."""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                from ...core.config import settings

                _embedder = SpeakerEmbedder(
                    source=settings.VOICE_SPEAKER_HF_SOURCE,
                    savedir=settings.VOICE_SPEAKER_MODEL_PATH,
                    device=settings.VOICE_SPEAKER_DEVICE,
                )
    return _embedder


def extract_acoustic_embedding(
    samples: np.ndarray, sample_rate: int, dim: Optional[int] = None
) -> np.ndarray:
    """Backward-compatible speaker embedding entrypoint.

    Delegates to the SpeechBrain ECAPA encoder. The ``dim`` argument is
    accepted for callers that still pass it, but the actual dimension is set by
    the loaded model (192 for ``spkrec-ecapa-voxceleb``) and is ignored here.
    """
    return get_speaker_embedder().extract(samples, sample_rate)


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
