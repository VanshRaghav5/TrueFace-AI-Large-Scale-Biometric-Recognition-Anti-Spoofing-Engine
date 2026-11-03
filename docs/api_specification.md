# TrueFace AI-X — API Specification (v1)

**Status:** Proposed Academic Prototype API Specification  
**Base Path:** `/api/v1`  
**Protocol:** HTTP/1.1 / JSON (multipart/form-data for media inputs)

---

## 1. Authentication & Common Headers

All protected endpoints require an authorization token or API key:

| Header | Type | Description |
|---|---|---|
| `Authorization` | `Bearer <token>` | JWT or API key for service access |
| `X-Request-ID` | `string (UUID)` | Correlation ID for audit logging and tracing |
| `Content-Type` | `string` | `application/json` or `multipart/form-data` |

---

## 2. Standard Decision Vocabulary & Reason Codes

Every authentication request produces an overall decision and machine-readable reason codes:

### Decision States (`overall_decision`)
- `allow`: Evidence meets acceptance policy for claimed identity and authenticity.
- `step_up`: Evidence is ambiguous, low-confidence, or requires alternative modality verification.
- `block`: Evidence meets rejection/spoof criteria or identity mismatch.
- `error`: System or processing failure; never defaults to `allow`.

### Standard Reason Codes
- `FACE_IDENTITY_MATCH`: Face embedding meets similarity threshold.
- `FACE_IDENTITY_MISMATCH`: Face embedding similarity below threshold.
- `FACE_QUALITY_LOW`: Blur, illumination, or face angle outside acceptable tolerance.
- `FACE_PAD_RISK`: Presentation attack detected (print, screen replay, mask).
- `FACE_MANIPULATION_RISK`: Deepfake, face swap, or synthetic generation artifact detected.
- `VOICE_IDENTITY_MATCH`: Speaker embedding meets similarity threshold.
- `VOICE_IDENTITY_MISMATCH`: Speaker embedding similarity below threshold.
- `AUDIO_QUALITY_LOW`: Insufficient speech energy, SNR too low, or audio too short.
- `AUDIO_SPOOF_RISK`: Synthetic speech (TTS) or voice cloning detected.
- `MODALITY_MISSING`: An expected modality was not supplied in the request.
- `MODEL_TIMEOUT`: Sub-model inference exceeded configured SLA timeout.
- `MODEL_UNAVAILABLE`: Configured model or checkpoint is offline or failed to initialize.
- `SIGNAL_CONFLICT`: Modalities provided contradictory identity or authenticity evidence.

---

## 3. Endpoints

### 3.1 Health & Diagnostics

#### `GET /api/v1/health`
Returns system status, active vector store, and model readiness.

**Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "1.0.0-academic",
  "vector_store": "faiss",
  "models": {
    "face_detector": "ready",
    "face_recognizer": "ready",
    "face_pad": "ready",
    "voice_vad": "ready",
    "voice_recognizer": "ready",
    "voice_antispoof": "ready"
  }
}
```

---

### 3.2 Enrollment

#### `POST /api/v1/enrollment`
Registers an identity into the controlled test gallery with explicit consent.

**Request (multipart/form-data):**
- `subject_id` (string): Pseudonymous subject identifier.
- `consent_confirmed` (boolean): Required consent assertion.
- `face_image` (file, optional): JPEG/PNG face image.
- `voice_sample` (file, optional): WAV audio sample (16kHz).

**Response `201 Created`:**
```json
{
  "enrollment_id": "enr_9b1deb4d",
  "subject_id": "subj_4821",
  "status": "success",
  "face_enrolled": true,
  "voice_enrolled": true,
  "enrolled_at": "2026-11-03T10:00:00Z"
}
```

---

### 3.3 Multimodal Authentication

#### `POST /api/v1/authentication/verify`
1:1 biometric verification against an enrolled `subject_id`.

**Request (multipart/form-data):**
- `subject_id` (string): Claimed identity.
- `face_image` (file, optional): Submitted face image.
- `voice_sample` (file, optional): Submitted voice clip.

**Response `200 OK`:**
```json
{
  "session_id": "auth_901cfa32",
  "claimed_subject_id": "subj_4821",
  "overall_decision": "allow",
  "fused_authenticity_score": 0.94,
  "fused_identity_score": 0.88,
  "reason_codes": [
    "FACE_IDENTITY_MATCH",
    "VOICE_IDENTITY_MATCH"
  ],
  "face_result": {
    "status": "available",
    "identity_score": 0.89,
    "liveness_score": 0.96,
    "deepfake_score": 0.98,
    "quality_score": 0.91
  },
  "voice_result": {
    "status": "available",
    "identity_score": 0.86,
    "antispoof_score": 0.93,
    "quality_score": 0.88
  },
  "evaluated_at": "2026-11-03T10:01:15Z"
}
```

---

### 3.4 Face Pipeline Inspection

#### `POST /api/v1/face/verify`
Performs face-only identity matching and authenticity checks.

#### `POST /api/v1/face/pad`
Evaluates Presentation Attack Detection only on a submitted image.

#### `POST /api/v1/face/deepfake`
Evaluates facial manipulation / deepfake probability only.

---

### 3.5 Voice Pipeline Inspection

#### `POST /api/v1/voice/verify`
Performs speaker verification against an enrolled reference voice template.

#### `POST /api/v1/voice/antispoof`
Evaluates synthetic speech, replay, and voice-cloning detection.

---

### 3.6 Audit & Compliance

#### `GET /api/v1/audit/events`
Lists verification audit events with query filtering.

**Query Parameters:**
- `limit` (integer, default: 20)
- `offset` (integer, default: 0)
- `decision` (string, optional: `allow`, `step_up`, `block`, `error`)

**Response `200 OK`:**
```json
{
  "total": 142,
  "items": [
    {
      "event_id": "evt_001",
      "timestamp": "2026-11-03T09:45:10Z",
      "subject_id": "subj_4821",
      "decision": "allow",
      "reason_codes": ["FACE_IDENTITY_MATCH"]
    }
  ]
}
```

