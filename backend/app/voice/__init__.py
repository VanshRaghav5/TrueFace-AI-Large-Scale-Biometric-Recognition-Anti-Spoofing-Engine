"""Voice modality processing for TrueFaceAI."""

from .voice_runtime import VoiceRuntime, voice_runtime
from .speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    VoiceProcessingError,
    compute_voice_similarity,
    extract_acoustic_embedding,
    parse_wav_bytes,
)
from .anti_spoofing.voice_antispoof import (
    VoiceAntispoofResult,
    evaluate_audio_antispoof,
)

__all__ = [
    "VoiceRuntime",
    "voice_runtime",
    "AudioQualityError",
    "InvalidAudioError",
    "VoiceProcessingError",
    "compute_voice_similarity",
    "extract_acoustic_embedding",
    "parse_wav_bytes",
    "VoiceAntispoofResult",
    "evaluate_audio_antispoof",
]
