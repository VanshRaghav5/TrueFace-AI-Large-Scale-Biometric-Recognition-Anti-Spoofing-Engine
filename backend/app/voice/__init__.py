"""Voice modality processing for TrueFaceAI."""

from .voice_runtime import VoiceRuntime, voice_runtime
from .speaker_verification.voice_engine import (
    AudioQualityError,
    InvalidAudioError,
    SpeakerModelUnavailableError,
    SpeakerEmbedder,
    VoiceProcessingError,
    compute_voice_similarity,
    extract_acoustic_embedding,
    get_speaker_embedder,
    parse_wav_bytes,
)
from .anti_spoofing.voice_antispoof import (
    AASISTDetector,
    AntispoofModelUnavailableError,
    VoiceAntispoofResult,
    evaluate_audio_antispoof,
    get_antispoof_detector,
)

__all__ = [
    "VoiceRuntime",
    "voice_runtime",
    "AudioQualityError",
    "InvalidAudioError",
    "SpeakerModelUnavailableError",
    "SpeakerEmbedder",
    "VoiceProcessingError",
    "compute_voice_similarity",
    "extract_acoustic_embedding",
    "get_speaker_embedder",
    "parse_wav_bytes",
    "AASISTDetector",
    "AntispoofModelUnavailableError",
    "VoiceAntispoofResult",
    "evaluate_audio_antispoof",
    "get_antispoof_detector",
]
