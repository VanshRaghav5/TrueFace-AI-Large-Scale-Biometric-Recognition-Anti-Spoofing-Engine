# Voice Recognition (Speaker Verification) Implementation

This document describes the speaker verification pipeline used by TrueFace AI-X,
how it replaces the previous placeholder acoustic template, and how to
configure and run it.

## Overview

Voice recognition is one biometric modality in the multi-gate pipeline. The
speaker encoder is [SpeechBrain](https://github.com/speechbrain/speechbrain)'s
**ECAPA-TDNN** model pretrained on **VoxCeleb**
(`speechbrain/spkrec-ecapa-voxceleb`). It produces a 192-dimensional
L2-normalized speaker embedding per utterance. Identity is verified by cosine
similarity against the subject's enrolled voice template.

Audio anti-spoofing (synthetic-speech / replay screening) runs as a separate,
independent analyzer and never doubles as identity evidence, in line with the
project rule that **a speaker match is not proof of live speech**.

## Architecture

```
WAV bytes
  └─ parse_wav_bytes()            decode + quality + speech-ratio VAD  (voice_engine.py)
        ├─ InvalidAudioError  -> VoiceResult(status=invalid)
        └─ AudioQualityError  -> VoiceResult(status=low_quality)
  └─ SpeakerEmbedder.extract()    ECAPA-TDNN embedding (offloaded, timed out) (voice_engine.py)
        ├─ SpeakerModelUnavailableError -> VoiceResult(status=model_unavailable)
        └─ TimeoutError              -> VoiceResult(status=timeout)
  └─ evaluate_audio_antispoof()   AASIST anti-spoof (offloaded) or heuristic fallback (voice_antispoof.py)
  └─ DB lookup + compute_voice_similarity()  vs enrolled VOICE template
        └─ dimension mismatch     -> reason_code VOICE_TEMPLATE_INCOMPATIBLE
```

Key files:

| File | Role |
| --- | --- |
| `backend/app/voice/speaker_verification/voice_engine.py` | WAV parsing, `SpeakerEmbedder` (ECAPA-TDNN), cosine similarity |
| `backend/app/voice/voice_runtime.py` | `VoiceRuntime`: extract, verify, anti-spoof, status, `initialize()` |
| `backend/app/voice/anti_spoofing/voice_antispoof.py` | AASIST anti-spoofing detector + heuristic fallback |
| `backend/app/voice/anti_spoofing/aasist_model.py` | AASIST PyTorch architecture (graph attention, SincConv) |
| `backend/app/services/enrollment_service.py` | Enrolls a VOICE template; degrades gracefully if the model is unavailable |
| `backend/app/services/authentication_service.py` | Consumes `VoiceResult` (contract unchanged) |
| `backend/app/api/v1/endpoints/voice.py` | `/voice/verify`, `/voice/antispoof` |

## Model loading

- The model is loaded **once** and reused for every request. Loading is
  decoupled from inference.
- `voice_runtime.initialize()` is called at FastAPI startup. A load failure is
  logged and recorded on `voice_runtime.status` but **does not stop the API
  from starting**; voice requests then return an explicit
  `model_unavailable` status while face/PIN/fusion continue to work.
- The first successful load downloads the weights from HuggingFace into
  `VOICE_SPEAKER_MODEL_PATH` (gitignored). Subsequent loads read from disk.
- On Windows, `LocalStrategy.COPY` is used instead of the default symlink
  strategy, which otherwise requires Developer Mode / admin privileges.

## Configuration

All keys are optional with sensible defaults (see `backend/app/core/config.py`
and `.env.example`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `VOICE_SPEAKER_ENABLED` | `true` | Enable the speaker encoder |
| `VOICE_SPEAKER_HF_SOURCE` | `speechbrain/spkrec-ecapa-voxceleb` | HuggingFace model id |
| `VOICE_SPEAKER_MODEL_PATH` | `models/voice/speaker_verification` | Local cache/save dir (gitignored) |
| `VOICE_SPEAKER_DEVICE` | `cpu` | Torch device for inference |
| `VOICE_EMBEDDING_DIMENSION` | `192` | Expected embedding dimension |
| `VOICE_INFERENCE_TIMEOUT` | `10.0` | Per-request inference timeout (seconds) |
| `VOICE_MATCH_THRESHOLD` | `0.70` | Cosine similarity accept threshold |
| `VOICE_LIVENESS_MIN_CONFIDENCE` | `0.80` | Heuristic fallback genuine-speech threshold |
| `VOICE_ANTISPOOF_ENABLED` | `true` | Enable the AASIST anti-spoofing model |
| `VOICE_ANTISPOOF_MODEL_PATH` | `models/voice/anti_spoofing/AASIST.pth` | Pretrained weights (tracked in git) |
| `VOICE_ANTISPOOF_DEVICE` | `cpu` | Torch device for AASIST inference |
| `VOICE_ANTISPOOF_THRESHOLD` | `0.5` | Bonafide softmax probability accept threshold |

> Threshold note: `VOICE_MATCH_THRESHOLD` is configurable and must be selected
> on **validation** data only, never tuned on the final test set. The default
> is a conservative operating point, not a measured/calibrated value.

## API contract (unchanged)

`VoiceResult` (`backend/app/schemas/voice.py`) is unchanged:

```json
{
  "status": "available",
  "speech_detected": true,
  "identity_similarity": 0.83,
  "antispoof_score": 0.91,
  "quality": { "duration_seconds": 3.2, "speech_ratio": 0.71, "snr_db": 22.4 },
  "reason_codes": ["VOICE_ANTISPOOF_BONA_FIDE", "VOICE_IDENTITY_MATCH"]
}
```

Status now additionally surfaces the explicit states defined in
`ModalityStatus`: `model_unavailable` and `timeout` (these were already in the
enum; the runtime now actually emits them for the voice path).

## Reason codes

Emitted by `VoiceRuntime.verify`:

- `VOICE_DECODE_ERROR:<detail>` — malformed WAV
- `VOICE_QUALITY_LOW:<detail>` — too short / low sample rate
- `VOICE_MODEL_UNAVAILABLE` / `VOICE_MODEL_ERROR:<detail>` — encoder could not load
- `MODEL_TIMEOUT` — inference exceeded `VOICE_INFERENCE_TIMEOUT`
- `VOICE_INFERENCE_ERROR:<detail>` — other inference failure
- `VOICE_ANTISPOOF_BONA_FIDE` / `AUDIO_SPOOF_RISK` + `VOICE_SYNTHETIC_SPEECH_DETECTED`
- `VOICE_IDENTITY_MATCH` / `VOICE_IDENTITY_MISMATCH`
- `VOICE_TEMPLATE_NOT_ENROLLED`
- `VOICE_TEMPLATE_INCOMPATIBLE` — stored template dimension differs from the current model
- `VOICE_DATABASE_SESSION_MISSING` — claimed identity provided but no DB session available
- `VOICE_CLAIMED_IDENTITY_OMITTED`

All reason codes are explicit: no silent success/failure paths exist.

## Privacy

- Raw audio is processed transiently and discarded; only the normalized
  embedding is persisted as a `BiometricTemplate` (modality `VOICE`).
- Embeddings are not returned to the client; only similarity and reason codes
  are exposed.
- Model weights are cached under `models/voice/` which is gitignored.

## Setup

```bash
pip install -r backend/requirements.txt   # includes speechbrain stack
# First run downloads the ECAPA weights into models/voice/speaker_verification/
uvicorn backend.app.main:app --reload
```

## Tests

```bash
pytest backend/tests/test_voice_engine.py -v
```

Pure-unit tests (WAV parsing, cosine math, anti-spoof) run without the model.
Integration tests (embedding shape/norm, determinism, AASIST detection) are
skipped automatically when the model is unavailable or not downloaded.

**Comprehensive pipeline tests:**
```bash
python scripts/test_voice_pipeline.py      # speaker verification flow
python scripts/test_antispoof_pipeline.py  # AASIST anti-spoofing flow
```

`test_antispoof_pipeline.py` tests 7 stages: model loading, synthetic audio
detection (sine, noise, harmonics), edge cases (empty, short, resampled),
public API dispatch, fallback heuristic labeling, AASIST-L variant, and config
verification. All tests must pass.

## Limitations

- Inference runs on the configured device (CPU by default). GPU via
  `VOICE_SPEAKER_DEVICE=cuda` or `VOICE_ANTISPOOF_DEVICE=cuda` requires a
  CUDA-enabled torch build.
- AASIST is pretrained on ASVspoof 2019 LA (logical access: TTS, voice
  conversion, replay). Physical access attacks (PA track) may require
  additional training or a PA-specific model.
- When AASIST weights are unavailable, the system falls back to an
  acoustic-spectral heuristic. The result's `model_name` field always
  identifies which engine ran (`aasist_aasist` vs `acoustic_spectral_fallback`),
  so degradation is explicit, never silent.
- Existing voice templates enrolled under a different embedding dimension are
  reported as `VOICE_TEMPLATE_INCOMPATIBLE` and do not silently match.
