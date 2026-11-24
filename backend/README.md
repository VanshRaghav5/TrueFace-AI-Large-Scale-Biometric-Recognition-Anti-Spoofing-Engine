# TrueFace AI-X Backend

FastAPI-based multimodal biometric authentication engine with face recognition, voice verification, PAD, and deepfake detection.

## Architecture

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── api/v1/                    # API endpoints
│   ├── core/                      # Configuration, security, logging
│   ├── db/                        # Database models and repositories
│   ├── face/                      # Face recognition pipeline
│   ├── voice/                     # Voice recognition pipeline
│   ├── search/                    # FAISS vector search
│   └── services/                  # Business logic
├── alembic/                       # Database migrations
└── tests/                         # Unit and integration tests
```

## Key Components

### Face Recognition Pipeline
- **Detection:** SCRFD face detector
- **Recognition:** ArcFace feature extraction (512-d embeddings)
- **Alignment:** 5-point facial landmark alignment
- **PAD:** MiniFASNet anti-spoofing
- **Deepfake:** Manipulation detection

### Voice Recognition Pipeline
- **Recognition:** ECAPA-TDNN speaker verification
- **VAD:** Voice Activity Detection
- **Anti-spoofing:** AASIST synthetic speech detection

### Vector Search
- **Engine:** FAISS IndexFlatIP (cosine similarity)
- **Gallery:** Dynamic in-memory index rebuilt from database
- **Operations:** 1:1 verification, 1:N identification

### Database
- **ORM:** SQLAlchemy (async)
- **Migrations:** Alembic
- **Models:** Subject, FaceTemplate, VoiceTemplate, AuditEvent

## API Endpoints

### Health Check
```
GET /api/v1/health
```
Returns system status, model availability, and database connectivity.

### Enrollment
```
POST /api/v1/enrollment
```
Enroll new biometric identity with consent verification.

**Form Data:**
- `subject_id` (required): Unique identifier
- `consent_confirmed` (required): "true"
- `face_image` (required): JPEG/PNG image
- `voice_sample` (optional): WAV audio file
- `security_pin` (optional): Knowledge factor

### Authentication
```
POST /api/v1/authentication/verify
```
Multimodal biometric verification with risk scoring.

**Form Data:**
- `face_image` (required): JPEG/PNG image
- `voice_sample` (optional): WAV audio file
- `claimed_subject_id` (optional): Identity claim
- `security_pin` (optional): Knowledge factor

**Response:**
```json
{
  "session_id": "uuid",
  "overall_decision": "allow|step_up|block|error",
  "fused_identity_score": 0.95,
  "fused_authenticity_score": 0.98,
  "face_result": { ... },
  "voice_result": { ... },
  "reason_codes": ["FACE_MATCH_HIGH", "REAL_FACE"],
  "latency_ms": 87
}
```

### Face Operations
```
POST /api/v1/face/verify      # Face-only verification
POST /api/v1/face/pad          # Liveness check
POST /api/v1/face/deepfake     # Deepfake detection
```

### Voice Operations
```
POST /api/v1/voice/verify      # Voice-only verification
POST /api/v1/voice/vad         # Voice activity detection
```

### Audit
```
GET /api/v1/audit              # List audit events
GET /api/v1/audit/{event_id}   # Get specific event
```

## Configuration

Environment variables (`.env`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Models
FACE_MODEL_NAME=buffalo_l
FACE_DETECTOR=scrfd_10g_bnkps
PAD_MODEL_PATH=models/pad/minifasnet.onnx
DEEPFAKE_MODEL_PATH=models/deepfake/detector.onnx
VOICE_MODEL_PATH=models/voice/ecapa_tdnn.onnx

# Thresholds
FACE_MATCH_THRESHOLD=0.75
VOICE_MATCH_THRESHOLD=0.70
PAD_REAL_THRESHOLD=0.80
DEEPFAKE_AUTH_THRESHOLD=0.70

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## Database Migrations

```bash
# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Development

```bash
# Activate venv (from project root)
source ../venv/bin/activate  # Linux/macOS
..\venv\Scripts\activate     # Windows

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/

# Check types
mypy app/

# Format code
black app/
isort app/
```

## Model Management

Models are loaded lazily on first use and cached in memory:

```python
from app.face.detection.scrfd import get_face_detector

detector = get_face_detector()  # Loads model if not cached
```

Model files should be placed in:
- `../models/face/` - Face recognition models
- `../models/voice/` - Voice recognition models  
- `../models/pad/` - Anti-spoofing models
- `../models/deepfake/` - Deepfake detection models

## Performance Optimization

### Parallel Processing
Use `authentication_service_optimized.py` for concurrent pipeline execution:
- Face detection + PAD + Deepfake in parallel
- Voice processing in parallel
- Target: <100ms latency

### Caching
- LRU cache for frequent embeddings
- In-memory FAISS index
- Model weight persistence

### Database
- Async SQLAlchemy for non-blocking I/O
- Connection pooling
- Indexed queries on subject_id

## Security

- **No raw media storage:** Images/audio processed transiently
- **Hashed PINs:** bcrypt with salt
- **SQL injection protection:** Parameterized queries
- **Input validation:** Pydantic models
- **Rate limiting:** TODO
- **API authentication:** TODO

## Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Coverage
pytest --cov=app tests/
```

## Troubleshooting

### Model loading fails
- Check model files exist in `../models/`
- Verify ONNX runtime installed: `pip install onnxruntime`
- Check GPU availability: `torch.cuda.is_available()`

### Database connection errors
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Run migrations: `alembic upgrade head`

### Slow inference
- Use GPU runtime: `pip install onnxruntime-gpu`
- Enable parallel processing
- Check CPU/memory usage

## Documentation

- [API Specification](../docs/api_specification.md)
- [Database Schema](../docs/database_schema.md)
- [Architecture](../docs/architecture.md)
- [Model Registry](../docs/model_registry.md)

## License

Academic research use only. See project root for full license.
