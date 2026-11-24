# TrueFace AI-X Project Structure

```
TrueFaceAI/
│
├── 📄 README.md                      # Main project documentation
├── 📄 requirements.txt               # Consolidated Python dependencies
├── 📄 .env.example                   # Environment configuration template
├── 📄 .gitignore                     # Git ignore rules
├── 📄 docker-compose.yml             # Multi-container orchestration
├── 📄 STRUCTURE.md                   # This file - project organization
│
├── 📁 venv/                          # Single virtual environment (gitignored)
│   └── (Python 3.10+ dependencies)
│
├── 📁 backend/                       # FastAPI Application
│   ├── 📄 README.md                  # Backend-specific documentation
│   ├── 📄 Dockerfile                 # Backend container configuration
│   ├── 📄 alembic.ini                # Database migration configuration
│   │
│   ├── 📁 alembic/                   # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 20261103_0001_face_templates.py
│   │       └── 20261108_0002_audit_events.py
│   │
│   ├── 📁 app/                       # Main application code
│   │   ├── main.py                   # FastAPI application entry
│   │   │
│   │   ├── 📁 api/                   # API layer
│   │   │   └── v1/
│   │   │       ├── router.py         # API router aggregation
│   │   │       └── endpoints/        # API endpoints
│   │   │           ├── health.py     # System health check
│   │   │           ├── enrollment.py # Biometric enrollment
│   │   │           ├── authentication.py # Multimodal verification
│   │   │           ├── face.py       # Face-specific operations
│   │   │           ├── voice.py      # Voice-specific operations
│   │   │           └── audit.py      # Audit log retrieval
│   │   │
│   │   ├── 📁 core/                  # Core utilities
│   │   │   ├── config.py             # Configuration management
│   │   │   ├── security.py           # Security utilities
│   │   │   ├── logging.py            # Structured logging
│   │   │   ├── exceptions.py         # Custom exceptions
│   │   │   └── cache.py              # LRU caching
│   │   │
│   │   ├── 📁 db/                    # Database layer
│   │   │   ├── database.py           # Database connection
│   │   │   ├── models/               # SQLAlchemy models
│   │   │   │   ├── subject.py
│   │   │   │   ├── template.py
│   │   │   │   └── audit.py
│   │   │   └── repositories/         # Data access layer
│   │   │       ├── subject_repository.py
│   │   │       └── audit_repository.py
│   │   │
│   │   ├── 📁 face/                  # Face recognition pipeline
│   │   │   ├── detection/            # Face detection
│   │   │   │   └── scrfd.py
│   │   │   ├── alignment/            # Face alignment
│   │   │   │   └── face_align.py
│   │   │   ├── liveness/             # Presentation attack detection
│   │   │   │   ├── antispoof_mn3.py
│   │   │   │   ├── minifasnet.py
│   │   │   │   ├── onnx_pad.py
│   │   │   │   └── orchestrator.py
│   │   │   └── deepfake/             # Deepfake detection
│   │   │       └── deepfake_detector.py
│   │   │
│   │   ├── 📁 voice/                 # Voice recognition pipeline
│   │   │   ├── recognition/          # Speaker verification
│   │   │   │   └── ecapa_tdnn.py
│   │   │   └── antispoof/            # Voice anti-spoofing
│   │   │       └── aasist.py
│   │   │
│   │   ├── 📁 search/                # Vector search
│   │   │   └── faiss_index.py        # FAISS-based similarity search
│   │   │
│   │   └── 📁 services/              # Business logic
│   │       ├── enrollment_service.py
│   │       ├── authentication_service.py
│   │       └── authentication_service_optimized.py
│   │
│   ├── 📁 tests/                     # Backend tests
│   │   ├── test_face_pipeline.py
│   │   └── test_api_endpoints.py
│   │
│   └── 📁 realtime/                  # Real-time face recognition demo
│       └── realtime_demo.py
│
├── 📁 frontend/                      # Next.js Dashboard
│   ├── 📄 README.md                  # Frontend-specific documentation
│   ├── 📄 package.json               # NPM dependencies
│   ├── 📄 Dockerfile                 # Frontend container configuration
│   ├── 📄 next.config.js             # Next.js configuration
│   ├── 📄 tailwind.config.ts         # Tailwind CSS configuration
│   ├── 📄 tsconfig.json              # TypeScript configuration
│   │
│   ├── 📁 src/                       # Source code
│   │   ├── 📁 app/                   # Next.js 14 App Router
│   │   │   ├── layout.tsx            # Root layout
│   │   │   ├── page.tsx              # Home page
│   │   │   ├── dashboard/            # System dashboard
│   │   │   ├── enrollment/           # Biometric enrollment
│   │   │   ├── authentication/       # Verification interface
│   │   │   ├── audit/                # Audit logs
│   │   │   ├── evaluation/           # Performance metrics
│   │   │   └── settings/             # Threshold configuration
│   │   │
│   │   ├── 📁 components/            # React components
│   │   │   ├── VoiceWave.tsx
│   │   │   ├── TerminalLog.tsx
│   │   │   ├── CameraPreview.tsx
│   │   │   ├── MetricDisplay.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── FileDropZone.tsx
│   │   │   ├── PipelineStepper.tsx
│   │   │   ├── VerificationStages.tsx
│   │   │   └── charts/               # Data visualizations
│   │   │       ├── ROCCurve.tsx
│   │   │       ├── PerformanceComparison.tsx
│   │   │       ├── LatencySparkline.tsx
│   │   │       ├── CircularGauge.tsx
│   │   │       └── VolumeChart.tsx
│   │   │
│   │   └── 📁 styles/                # Global styles
│   │       └── globals.css
│   │
│   ├── 📁 public/                    # Static assets
│   └── 📁 tests/                     # Frontend tests
│
├── 📁 docs/                          # Documentation
│   ├── 📄 prd.md                     # Product Requirements
│   ├── 📄 architecture.md            # Technical Architecture
│   ├── 📄 api_specification.md       # API Documentation
│   ├── 📄 database_schema.md         # Database Design
│   ├── 📄 design_system.md           # UI/UX Design System
│   ├── 📄 model_registry.md          # Model Specifications
│   ├── 📄 agents.md                  # Agent Automation
│   │
│   ├── 📁 implementation/            # Implementation guides
│   │   ├── face_recognition_implementation.md
│   │   ├── voice_recognition_implementation.md
│   │   ├── voice_antispoofing_implementation.md
│   │   ├── pad_real_inference_readiness.md
│   │   └── realtime_face_recognition.md
│   │
│   ├── 📁 frontend/                  # Frontend documentation
│   │   ├── frontend_modernization.md
│   │   └── purple_theme_voice_animation.md
│   │
│   └── 📁 decisions/                 # Architecture Decision Records
│       └── architecture_decisions.md
│
├── 📁 models/                        # Model weights (gitignored)
│   ├── face/                         # Face recognition models
│   ├── voice/                        # Voice recognition models
│   ├── pad/                          # Anti-spoofing models
│   └── deepfake/                     # Deepfake detection models
│
├── 📁 evaluation/                    # Evaluation & benchmarking
│   ├── datasets/                     # Test datasets
│   ├── scripts/                      # Evaluation scripts
│   └── results/                      # Benchmark results
│
├── 📁 scripts/                       # Utility scripts
│   ├── setup_environment.sh
│   ├── download_models.py
│   └── run_benchmarks.py
│
├── 📁 tests/                         # Integration tests
│   └── e2e/                          # End-to-end tests
│
└── 📁 infra/                         # Infrastructure
    ├── docker/                       # Docker configurations
    └── ci/                           # CI/CD pipelines
```

## Key Principles

### 1. Single Virtual Environment
- **Location:** `./venv/` at project root
- **Purpose:** All Python dependencies for backend, testing, and evaluation
- **Installation:** `pip install -r requirements.txt`

### 2. Clear Separation
- **Backend:** Pure Python/FastAPI application
- **Frontend:** Pure Node.js/Next.js application  
- **Docs:** Markdown documentation
- **Models:** Gitignored binary files

### 3. Modular Architecture
- Each module has clear responsibility
- Loose coupling between components
- Easy to test and maintain

### 4. Documentation Standards
- Root README: Project overview and quickstart
- Backend README: API and service documentation
- Frontend README: UI components and development
- Docs folder: Detailed technical specifications

## Development Workflow

```bash
# 1. Activate single venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# 2. Backend development
cd backend
uvicorn app.main:app --reload

# 3. Frontend development (separate terminal)
cd frontend
npm run dev

# 4. Run tests
pytest tests/
pytest backend/tests/
npm test --prefix frontend
```

## Notes
- All `.venv/` directories removed except root `venv/`
- Backend `requirements.txt` removed (consolidated to root)
- Docs reorganized by category
- Clear gitignore for models and datasets
