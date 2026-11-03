# TrueFace AI-X — Model Registry & Benchmark Specifications

**Purpose:** Document the candidate model architectures, input/output contracts, target licenses, and baseline checkpoints for the biometric recognition and anti-spoofing pipelines.

> Note: All models are bounded deterministic components. No LLM or generative agent is placed in the biometric verification path.

---

## 1. Summary of Pipelines and Components

| Modality | Task | Candidate Architecture | Input Specs | Output Specs | Target License |
|---|---|---|---|---|---|
| **Face** | Detection & Alignment | RetinaFace / MediaPipe | 640x640x3 RGB | 5 landmarks, Bounding Box | MIT / Apache 2.0 |
| **Face** | Identity Recognition | ArcFace (ResNet-50 / iResNet) | 112x112x3 aligned RGB | 512-d normalized vector | MIT / Academic |
| **Face** | Presentation Attack Detection (PAD) | MiniFASNet / anti-spoof-mn3 | Model-specific: 80x80 BGR ensemble or 128x128 BGR | Model-specific calibrated bona-fide score | NOT CLEARED; verify source, weights and dataset terms |
| **Face** | Deepfake / Manipulation Detection | EfficientNet-B4 / MesoNet | 224x224x3 cropped face | Fake probability [0, 1] | Apache 2.0 |
| **Voice** | Voice Activity Detection (VAD) | Silero VAD / WebRTC VAD | 16kHz mono audio | Speech intervals / segments | MIT |
| **Voice** | Speaker Verification | ECAPA-TDNN / ResNetSE34V2 | 16kHz audio (>= 3s) | 192-d or 256-d embedding | Apache 2.0 / MIT |
| **Voice** | Audio Anti-spoofing | AASIST / RawNet2 | Raw waveform (16kHz) | Spoof score / prob [0, 1] | Academic / MIT |

---

## 2. Component Pipeline Details

### 2.1 Face Recognition Branch
- **Detector:** Identifies bounding boxes and primary facial landmarks (eyes, nose, mouth corners).
- **Alignment:** Affine transformation aligned to standard 112x112 coordinates.
- **Quality Check:** Evaluates sharpness (Laplacian variance) and illumination. Rejects low-quality frames.
- **Embedding:** ArcFace backbone generates unit-length $L_2$-normalized 512-dimensional vector.
- **Distance Metric:** Cosine similarity ($[-1.0, 1.0]$ mapped to $[0.0, 1.0]$).

### 2.2 Face Presentation Attack Detection (PAD)
- **Target Attacks:** 2D photo prints (matte/glossy), screen replay attacks (tablets/phones).
- **Output:** Calibrated authenticity score $S_{pad} \in [0.0, 1.0]$ where $1.0$ is genuine live presentation.
- **anti-spoof-mn3 candidate:** The separate adapter expects the OMZ converted
  artifact's 128x128 BGR input, applies the documented mean/scale
  normalization, and interprets output class 0 as real and class 1 as spoof.
  The artifact remains NOT CLEARED; no weights are stored or executed.

### 2.3 Face Deepfake Detection
- **Target Attacks:** AI face swap, facial reenactment, diffusion-generated faces.
- **Output:** Manipulation confidence score $S_{deepfake} \in [0.0, 1.0]$ where $1.0$ indicates authentic, unmanipulated face.

### 2.4 Voice Processing Branch
- **VAD Preprocessing:** Filters out silence and ambient non-speech noise. Trims audio to valid speech frames.
- **Speaker Embedding:** Generates identity vector from processed speech frames.
- **Distance Metric:** Cosine similarity against enrolled voice template.

### 2.5 Audio Anti-spoofing (ASVspoof)
- **Target Attacks:** Text-to-Speech (TTS) synthesis, Voice Conversion (VC), recorded acoustic replay.
- **Output:** Genuine speech score $S_{antispoof} \in [0.0, 1.0]$.

---

## 3. Storage and Asset Locations

Model weights and checkpoints are strictly excluded from git tracking and stored locally:
```text
models/
├── face/
│   ├── detection/
│   └── recognition/
├── voice/
│   ├── vad/
│   └── speaker_verification/
├── liveness/
│   └── anti-spoof-mn3.onnx
├── deepfake/
│   └── manipulation_model.onnx
└── audio_antispoof/
    └── synthetic_speech_model.onnx
```
