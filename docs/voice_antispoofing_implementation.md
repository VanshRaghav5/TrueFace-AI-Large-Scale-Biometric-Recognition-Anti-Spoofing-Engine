# Voice Anti-Spoofing (AASIST) Implementation

This document describes the voice anti-spoofing pipeline: how AASIST replaces
the previous spectral heuristic, how the fallback works, and how to configure
and test it.

## Overview

Voice anti-spoofing detects synthetic speech, voice cloning, text-to-speech
(TTS), and replay attacks. It runs as a **separate, independent analyzer** from
speaker verification — a speaker match is never treated as proof of live
speech, and anti-spoofing evidence is never used as identity evidence.

The primary engine is **AASIST** (Audio Anti-Spoofing using Integrated
Spectro-Temporal graph attention networks), pretrained on the **ASVspoof 2019
LA** (Logical Access) dataset. The model ingests a raw waveform and outputs a
two-class classification: bona-fide (real human speech) vs. spoof.

- **AASIST**: 1.22 MB weights, EER 0.83% on ASVspoof 2019 LA
- **AASIST-L**: 0.41 MB weights, 85,306 parameters, EER 0.99%

Pretrained weights are bundled with the project (tracked in git, unlike the
speaker model which is downloaded from HuggingFace).

## Architecture

```
WAV samples (float32, mono)
  └─ Resample to 16 kHz if needed
  └─ pad_audio()              truncate or tile to 64,600 samples (~4 s)
  └─ AASIST Model.forward()
        ├─ SincConv front-end (learnable sinc filterbank)
        ├─ Residual encoder blocks
        ├─ Spectral GAT (GAT-S)  +  Temporal GAT (GAT-T)
        ├─ Hierarchical graph attention (HtrgGAT) with master nodes
        └─ Linear output layer → (batch, 2) logits
  └─ softmax(logits)
        ├─ bona_fide_prob = probs[1]   (genuine speech probability)
        └─ spoof_prob     = probs[0]
  └─ classify:
        ├─ bona_fide_prob >= threshold        → state = "bona_fide"
        ├─ bona_fide_prob <= threshold - 0.25  → state = "synthetic"
        └─ otherwise                           → state = "uncertain"
```

### Fallback path (when AASIST is unavailable)

If the weights file is missing, `VOICE_ANTISPOOF_ENABLED=false`, or PyTorch is
not installed, the system falls back to an acoustic-spectral heuristic that
analyzes high-frequency energy ratio, spectral flatness, and temporal
modulation. The result's `model_name` is `acoustic_spectral_fallback` and
`details.fallback_reason` is set to `aasist_model_unavailable`, so callers can
always detect degradation explicitly.

## Key files

| File | Role |
| --- | --- |
| `backend/app/voice/anti_spoofing/aasist_model.py` | AASIST PyTorch architecture (GraphAttentionLayer, SincConv, Model) + config + `pad_audio` |
| `backend/app/voice/anti_spoofing/voice_antispoof.py` | `AASISTDetector`, `evaluate_audio_antispoof()`, heuristic fallback, `get_antispoof_detector()` |
| `backend/app/voice/anti_spoofing/__init__.py` | Package exports |
| `backend/app/voice/voice_runtime.py` | `VoiceRuntime.initialize()` loads AASIST; `verify()` runs anti-spoof off the event loop |
| `backend/app/core/config.py` | `VOICE_ANTISPOOF_*` settings |
| `backend/app/api/v1/endpoints/voice.py` | `/voice/antispoof` endpoint (async) |
| `backend/app/api/v1/endpoints/health.py` | Reports `antispoof_initialized`, `antispoof_model_name`, `antispoof_error` |
| `models/voice/anti_spoofing/AASIST.pth` | Pretrained AASIST weights (tracked in git) |
| `models/voice/anti_spoofing/AASIST-L.pth` | Pretrained AASIST-L weights (tracked in git) |

## Model loading

- AASIST is loaded **once** at startup via `voice_runtime.initialize()` and
  reused for every request. Loading is decoupled from inference.
- The model variant (AASIST vs AASIST-L) is auto-detected from the weights
  filename (`AASIST-L.pth` → AASIST-L config; everything else → AASIST config).
- A load failure is logged and recorded on `voice_runtime.status` but does
  **not stop the API**. Anti-spoofing degrades to the explicitly-labeled
  heuristic fallback while speaker verification and all other modalities
  continue to work.
- Weights are bundled in the repo (small files). No download is required.

## Configuration

All keys are optional with sensible defaults (see `config.py` and `.env`):

| Setting | Default | Meaning |
| --- | --- | --- |
| `VOICE_ANTISPOOF_ENABLED` | `true` | Enable the AASIST model |
| `VOICE_ANTISPOOF_MODEL_PATH` | `models/voice/anti_spoofing/AASIST.pth` | Pretrained weights path |
| `VOICE_ANTISPOOF_DEVICE` | `cpu` | Torch device for inference |
| `VOICE_ANTISPOOF_THRESHOLD` | `0.5` | Bonafide softmax probability threshold |

To switch to the lighter AASIST-L model:

```env
VOICE_ANTISPOOF_MODEL_PATH=models/voice/anti_spoofing/AASIST-L.pth
```

## Result interface

`VoiceAntispoofResult` (dataclass, unchanged fields):

```python
@dataclass(frozen=True)
class VoiceAntispoofResult:
    genuine_probability: float   # 1.0 = live human speech, 0.0 = synthetic
    spoof_probability: float      # 1.0 = synthetic/spoof
    is_synthetic_speech: bool
    state: str                    # "bona_fide", "synthetic", "uncertain"
    model_name: str               # "aasist_aasist" | "aasist_aasist-l" | "acoustic_spectral_fallback"
    details: dict                # model-specific (logits, probs, num_samples, threshold)
```

The `model_name` field always identifies which engine produced the result, so
degradation is explicit and never silent.

## API endpoints

### `POST /api/v1/voice/antispoof`

Upload a WAV file; returns the anti-spoofing evaluation:

```json
{
  "status": "available",
  "speech_detected": true,
  "duration_seconds": 4.0,
  "genuine_probability": 0.02,
  "spoof_probability": 0.98,
  "is_synthetic_speech": true,
  "state": "synthetic",
  "model_name": "aasist_aasist",
  "details": {
    "bonafide_logit": -9.65,
    "spoof_logit": 8.63,
    "bonafide_prob": 0.02,
    "spoof_prob": 0.98,
    "num_samples": 64600,
    "model": "aasist_aasist",
    "threshold": 0.5
  }
}
```

### `POST /api/v1/voice/verify`

The verification endpoint runs anti-spoofing as part of the full flow. If
`is_synthetic_speech` is true, `AUDIO_SPOOF_RISK` and
`VOICE_SYNTHETIC_SPEECH_DETECTED` reason codes are emitted, and identity match
is blocked even when cosine similarity is high.

### `GET /api/v1/health`

The health endpoint reports:

```json
{
  "models": {
    "voice": {
      "status": "ready",
      "antispoof": "ready",
      "antispoof_model_name": "aasist_aasist",
      "antispoof_error": null
    },
    "voice_antispoof": "ready"
  }
}
```

When AASIST is unavailable, `antispoof` becomes `"fallback"` and
`voice_antispoof` becomes `"fallback"`.

## Dashboard

The frontend dashboard (`frontend/src/app/dashboard/page.tsx`) shows the
anti-spoofing status under the Voice Pipeline Status card:

- **Anti-Spoof: AASIST** (emerald) — AASIST model loaded
- **Anti-Spoof: Fallback** (warning) — heuristic fallback active

## Audio preprocessing

1. **Resample**: if the input sample rate ≠ 16 kHz, the signal is resampled
   using `scipy.signal.resample`.
2. **Pad/truncate**: the waveform is padded or truncated to exactly 64,600
   samples (~4 seconds at 16 kHz). Shorter signals are **tiled** (repeated),
   matching the original AASIST evaluation protocol. Longer signals take the
   first 64,600 samples.
3. **Tensor**: converted to `float32`, shape `(1, 64600)`, moved to device.

## Tests

### Unit + integration tests

```bash
pytest backend/tests/test_voice_engine.py -v
```

Includes 5 AASIST-specific tests (model-gated with `needs_antispoof_model`):
- `test_aasist_detects_synthetic_audio` — sine wave → synthetic
- `test_aasist_handles_short_audio` — 0.5s signal padded to 64600
- `test_aasist_empty_signal` — empty array → synthetic with error flag
- `test_aasist_resamples_nonstandard_rate` — 8 kHz input resampled to 16 kHz
- `test_antispoof_result_model_name_explicit` — model_name always set

### Comprehensive pipeline test

```bash
python scripts/test_antispoof_pipeline.py
```

Tests 7 stages:
1. AASIST model loading (variant detection, load time)
2. Synthetic audio detection (sine, white noise, harmonic signal)
3. Edge cases (empty signal, short audio padding, non-standard sample rate)
4. Public API dispatch (`evaluate_audio_antispoof` → AASIST or fallback)
5. Fallback heuristic labeling (explicit `model_name` + `fallback_reason`)
6. AASIST-L variant (separate detector instance, correct model_name)
7. Config verification (all `VOICE_ANTISPOOF_*` settings)

All tests use ASCII markers (`[OK]`/`[FAIL]`/`[WARN]`) for Windows console
compatibility.

## Limitations

- AASIST is pretrained on **ASVspoof 2019 LA** (logical access: TTS, voice
  conversion, replay). Physical access attacks (PA track: speaker-side
  replay through loudspeakers) may require a PA-trained model.
- The threshold (0.5 default) is a starting point. For production, calibrate
  on validation data to achieve the desired false-accept / false-reject
  tradeoff. The ASVspoof 2019 LA EER threshold corresponds to a different
  operating point than a simple 0.5 softmax cutoff.
- Inference runs on CPU by default. GPU via `VOICE_ANTISPOOF_DEVICE=cuda`
  requires a CUDA-enabled torch build. Model is small (~72K params for AASIST,
  ~85K for AASIST-L), so CPU inference is fast (~0.1s).
- The heuristic fallback is significantly weaker than AASIST. It should be
  treated as an explicit degraded state, not a production-grade detector.

## Reference

- **Paper**: Jung et al., "AASIST: Audio Anti-Spoofing using Integrated
  Spectro-Temporal Graph Attention Networks", arXiv:2110.01200 (2021).
- **Original repo**: https://github.com/clovaai/aasist
- **Dataset**: ASVspoof 2019 LA, https://www.asvspoof.org/index2019.html
- **License**: MIT (NAVER Corp.)
