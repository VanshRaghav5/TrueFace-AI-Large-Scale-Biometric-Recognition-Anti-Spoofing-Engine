# TrueFace AI-X — Architecture Decision Records (ADRs)

---

## ADR 001: Academic Prototype Technology Stack Selection

- **Status:** Approved
- **Context:** TrueFace AI-X is an academic research prototype evaluating multimodal biometric authentication, presentation attack detection, and deepfake verification. The stack must support rapid research prototyping, clean separation of concerns, and robust machine learning inference.
- **Decision:**
  - **Frontend:** Next.js (App Router), React, Tailwind CSS for reactive UI, biometric capture preview, and evaluation dashboard.
  - **Backend / Orchestration:** FastAPI (Python 3.10+) for async request orchestration, typed Pydantic schemas, and native integration with PyTorch/ONNX.
  - **Metadata & Audit:** PostgreSQL 16+ via async SQLAlchemy.
  - **Vector Search:** FAISS (Flat/IVF) for controlled test gallery search.
- **Consequences:** Provides reproducible Python environment for ML pipelines while maintaining a modern web interface.

---

## ADR 002: Deterministic Decision Engine vs. Autonomous LLMs

- **Status:** Approved / Enforced
- **Context:** Modern AI systems sometimes incorporate LLMs for agentic orchestration. In biometric security, probabilistic LLM decisions can introduce hallucination, non-determinism, and vulnerability to adversarial prompt injection.
- **Decision:** Autonomous LLMs and agent frameworks are strictly prohibited in the biometric verification and decision path. All authentication decisions must be calculated deterministically via score calibration, weighted fusion, and explicit rule-based risk policies.
- **Consequences:** Eliminates stochastic decision variation; guarantees complete explainability through deterministic reason codes.

---

## ADR 003: Decoupling Identity Matching from Authenticity & Liveness

- **Status:** Approved
- **Context:** Traditional biometric systems often treat a high cosine similarity match as sufficient proof of authentication. High-quality presentation attacks (printed photos, replay screens) and deepfakes can produce high similarity scores while being fraudulent.
- **Decision:** The system strictly separates **Identity** (who is the subject?) from **Authenticity** (is the media presentation genuine and live?). Both must independently satisfy policy thresholds. A match without confirmed liveness results in `block` or `step_up`, never `allow`.
- **Consequences:** Architecture requires dedicated PAD and deepfake detection pipelines parallel to feature extraction.

---

## ADR 004: Vector Search Architecture (FAISS vs. Distributed Vector DB)

- **Status:** Approved
- **Context:** The project requires 1:N face search across a controlled gallery of test subjects.
- **Decision:** Implement an abstract `VectorStore` interface with a concrete `FAISSStore` implementation for local, in-memory/file-based index evaluation. Qdrant or Milvus will only be considered if gallery size expands beyond local memory limits.
- **Consequences:** Minimizes infrastructure overhead during academic experimentation while preserving an easy migration path.

---

## ADR 005: Privacy by Default and Ephemeral Biometric Media

- **Status:** Approved
- **Context:** Biometric data is sensitive personal data. Compliance with privacy principles requires minimizing data retention and preventing accidental leakage.
- **Decision:**
  - Raw biometric media (images, audio clips) are processed in-memory and are never written to disk or recorded in logs.
  - Only pseudonymous identifiers (`subj_xxxx`) are linked to template indices.
  - Full raw floating-point embeddings are masked in application logs and API responses.
- **Consequences:** System prevents biometric template harvesting from logs and database dumps.

---

## ADR 006: Decision Policy and the Never-Silent-Allow Invariant

- **Status:** Approved
- **Context:** Failures such as model timeouts, missing modalities, image blur, corrupted audio, or unhandled exceptions must never degrade insecurely.
- **Decision:** Under no circumstance shall any error, timeout, missing input, low-quality sample, or conflicting signal default to `allow`. All failures must explicitly resolve to `step_up`, `block`, or `error`.
- **Consequences:** Ensures defense-in-depth and prevents fail-open security bypasses.

