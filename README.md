# TrueFace AI-X: Multimodal Biometric Recognition, Deepfake Detection & Anti-Spoofing Engine

TrueFace AI-X is an academic research prototype evaluating whether combining face and voice identity and authenticity signals improves verification reliability over single-modality baselines.

---

## Key Capabilities

- **Consent-based Enrollment:** Authorizes and stores test biometric templates with explicit consent records.
- **Face Processing Branch:** Face detection, facial landmark alignment, 512-d feature extraction, 1:1 verification, controlled-gallery 1:N search, Presentation Attack Detection (PAD), and deepfake/manipulation detection.
- **Voice Processing Branch:** Voice Activity Detection (VAD), audio normalization, speaker embedding extraction, 1:1 speaker verification, and synthetic speech/audio replay anti-spoofing.
- **Vector Search:** Controlled test gallery indexing via FAISS with pseudonymous internal identity mapping.
- **Multimodal Fusion & Risk Engine:** Calibrated score fusion, risk policy evaluation, and explainable decision gating (`allow`, `step_up`, `block`, `error`) accompanied by machine-readable reason codes.
- **Interactive Dashboard:** Next.js + React + Tailwind CSS client for biometric enrollment, authentication walkthrough, verification results, audit inspection, and evaluation visualization.

---

## System Architecture

```text
TrueFace-AI-X/
├── docs/                 # PRD, Architecture, Design System, API & DB Specs
├── frontend/             # Next.js 14+ / React / Tailwind CSS Dashboard
├── backend/              # FastAPI Application, Pipelines, Search, Fusion Engine
├── evaluation/           # Datasets, Experiment Scripts, Metrics, Reports
├── models/               # Model weights and checkpoint directories (gitignored)
├── scripts/              # Environment setup, preprocessing, and benchmark scripts
├── tests/                # System-level E2E, security, and integration tests
└── infra/                # Docker and CI/CD automation configurations
```

---

## Quickstart

### Prerequisites

- Python 3.10+ (64-bit)
- Node.js 18+ and npm
- Docker & Docker Compose (optional for containerized deployment)
- CUDA-compatible GPU (recommended for local model inference; CPU execution supported)

### 1. Environment Setup

```bash
# Clone the repository and enter the directory
git clone <repository-url>
cd TrueFaceAI

# Copy environment configuration
cp .env.example .env

# Set up Python backend virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Backend (FastAPI)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The OpenAPI documentation will be accessible at: `http://localhost:8000/docs`

### 3. Run Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

The web dashboard will be available at: `http://localhost:3000`

### 4. Containerized Execution (Docker Compose)

```bash
docker-compose up --build
```

---

## Documentation

- [Product Requirements Document](docs/prd.md)
- [Technical Architecture](docs/architecture.md)
- [Design System](docs/design_system.md)
- [Agent & Automation Rules](docs/agents.md)
- [API Specification](docs/api_specification.md)
- [Database Schema](docs/database_schema.md)
- [Model Registry](docs/model_registry.md)
- [Architecture Decision Records](docs/decisions/architecture_decisions.md)

---

## Privacy, Security & Ethical Boundaries

- **Consent Required:** Biometric enrollment strictly requires explicit consent verification.
- **Privacy by Design:** No raw biometric media, audio waveforms, or full raw embeddings are retained in logs or transmitted across public endpoints.
- **Deterministic Risk Engine:** No autonomous or hallucinating LLMs are permitted in the biometric authentication decision path.
- **Academic Scope:** TrueFace AI-X is a research prototype developed for academic evaluation and is not certified for production high-risk access control.

