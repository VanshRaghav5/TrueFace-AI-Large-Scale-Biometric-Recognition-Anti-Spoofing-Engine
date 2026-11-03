# TrueFace AI-X — Product Requirements Document

**Project:** TrueFace AI-X: Multimodal Biometric Recognition, Deepfake Detection & Anti-Spoofing Engine  
**Institution:** GLA University, Department of Computer Science and Engineering  
**Course:** B.Tech CSE (AIML & IoT), IV Year — VII Semester, Academic Year 2026–2027  
**Document purpose:** Product definition and implementation reference for the project team and Claude Code.

> **Status:** This document translates the approved project synopsis into an implementation-oriented PRD. The synopsis describes a proposed academic prototype. Items marked **TBD**, **proposed**, or **to be finalized** must not be treated as already implemented or approved.

---

## 1. Product summary

TrueFace AI-X is an academic prototype for evaluating multimodal biometric authentication. It combines two distinct questions:

1. **Identity:** Does the submitted face or voice sample match an enrolled identity?
2. **Authenticity:** Does the submitted media appear genuine under the supported liveness, presentation-attack, manipulation, replay, or synthetic-speech checks?

The system combines available modality signals through a documented fusion/risk layer and returns one of three primary outcomes:

- **Allow** — available evidence meets the configured acceptance policy.
- **Step-up Verification** — evidence is missing, conflicting, low-confidence, or requires another permitted check.
- **Block** — evidence meets a configured rejection/risk policy.

The product must explain decisions using reason codes. It must not imply that any single detector proves authenticity.

## 2. Problem statement

Face recognition can be attacked with printed photographs, screen replays, masks, or manipulated media. Face matching can also degrade with lighting, pose, image quality, and camera changes. Voice authentication faces replayed recordings, synthetic speech, and voice-cloning attempts. A system that checks identity without checking whether the biometric evidence is genuine can make unsafe decisions.

TrueFace AI-X evaluates whether combining face and voice identity/authenticity evidence improves robustness compared with face-only and voice-only baselines.

## 3. Goals

- Demonstrate consent-based enrollment of controlled test identities.
- Implement face detection/alignment, embedding generation, 1:1 verification, and controlled-gallery 1:N search.
- Evaluate face liveness / presentation-attack detection (PAD).
- Evaluate face-manipulation / deepfake classification.
- Implement voice activity detection (VAD), audio preprocessing, speaker embeddings, and speaker verification.
- Evaluate audio replay / synthetic-speech anti-spoofing for supported attack classes.
- Calibrate modality scores and implement a documented multimodal fusion/risk policy.
- Provide FastAPI endpoints and a web dashboard for enrollment, authentication, explanations, and audit review.
- Store required metadata and audit events in PostgreSQL; use FAISS initially or Qdrant if justified.
- Produce reproducible evaluation results comparing face-only, voice-only, and fused modes.

## 4. Non-goals and boundaries

The prototype is **not**:
- A certified or production-ready access-control product.
- A guarantee that all spoofing or deepfakes will be detected.
- A legal identity-verification system.
- A national-scale or million-identity production search service.
- A campus-door, banking, law-enforcement, or unrestricted surveillance integration.
- A production mobile application.
- A system that trains large foundation models from scratch.
- A system with a guaranteed sub-500 ms response time or universal hardware performance.

Do not add out-of-scope capabilities without an explicit project decision.

## 5. Users and roles

### Authorized user
- Completes an authentication attempt using permitted face and voice samples.
- Sees a clear result and human-readable explanation.
- Can understand retry, missing-modality, and permission states.

### Administrator
- Manages consented enrollment.
- Reviews authorized audit events.
- Has privileged access only to the functions required for the prototype.

### Evaluator / researcher
- Runs experiments on approved test sets.
- Compares face-only, voice-only, and fused results.
- Inspects aggregate metrics, error breakdowns, and evaluation records.

These are prototype personas, not claims of deployment in a real institution.

## 6. Core user journeys

### 6.1 Enrollment
1. Administrator authenticates and is authorized to enroll.
2. Consent is explicitly recorded before enrollment.
3. Permitted face and/or voice samples are captured or uploaded.
4. Input type, size, duration, and quality are validated.
5. Relevant preprocessing and model inference generate reference embeddings.
6. Store pseudonymous identity metadata, modality, model/embedding version, and protected reference metadata.
7. Return enrollment/reference identifiers.
8. Do not retain raw media by default; any exception requires an explicitly approved retention rule.

### 6.2 Authentication
1. User submits permitted face image/clip and audio sample (or supported capture references), with an optional claimed identity.
2. API authenticates the application account and validates authorization.
3. Validate media format, size, duration, and quality.
4. Face and voice branches run independently where input is available:
   - Face: detection/alignment, identity embedding/search, PAD/liveness, manipulation detection.
   - Voice: VAD/audio preprocessing, speaker embedding/verification, audio anti-spoof.
5. Return structured modality results to the fusion/risk layer.
6. Calibrate compatible scores using validation-selected parameters.
7. Apply the documented decision policy.
8. Write a minimal audit event.
9. Return decision, reason codes, scores suitable for the UI, and measured latency.
10. Missing, low-quality, timed-out, or failed modalities must never silently produce **Allow**.

### 6.3 Evaluation
1. Select an approved dataset and predefined train/validation/test split.
2. Confirm dataset license, labels, class balance, and identity/session separation where applicable.
3. Run each task independently before fusion.
4. Select thresholds using validation data only.
5. Evaluate on held-out test data.
6. Compare face-only, voice-only, and fused modes.
7. Record model versions, data split, configuration, random seed where applicable, hardware, and metrics.
8. Export aggregate results and document limitations/failure cases.

## 7. Functional requirements

| ID | Requirement | Priority | Acceptance evidence |
|---|---|---|---|
| FR-01 | Consent-based enrollment of permitted test identities | Must | Enrollment cannot proceed without consent and authorization |
| FR-02 | Face detection/alignment and embedding generation | Must | Valid face input produces a versioned embedding/result or explicit error |
| FR-03 | 1:1 face verification | Must | Match/no-match and score under a documented threshold |
| FR-04 | Controlled-gallery 1:N face search | Must | Ranked candidates with documented search behavior and identity mapping |
| FR-05 | Face liveness/PAD | Must | Score/class for supported attacks; held-out evaluation documented |
| FR-06 | Face manipulation/deepfake classification | Should | Result and supported limitations documented |
| FR-07 | VAD, audio preprocessing, speaker embedding and verification | Must | Speaker match/score with documented threshold |
| FR-08 | Audio replay/synthetic-speech anti-spoofing | Must/Should, feasibility-dependent | Evaluation on labeled supported attack classes |
| FR-09 | Score calibration and fusion/risk decision | Must | Genuine, mismatch, spoof, missing-modality, and conflict tests |
| FR-10 | Allow / Step-up Verification / Block outcomes | Must | Deterministic policy and reason codes returned |
| FR-11 | FastAPI integration | Must | Critical endpoints pass API tests |
| FR-12 | Web dashboard | Must | Enrollment/authentication/result/audit journeys work end-to-end |
| FR-13 | PostgreSQL metadata and audit events | Must | Persistence, authorization, and audit tests pass |
| FR-14 | Evaluation reports and reproducibility metadata | Must | Results include dataset split, model version, threshold, environment |
| FR-15 | Health endpoint and model-version visibility | Must | Health response reports service and loaded model versions |

## 8. Proposed API surface

The synopsis proposes the following API snapshot. Exact request/response schemas, token implementation, and status-code details must be finalized in the API specification.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/enroll` | POST | Consent-based enrollment of an authorized test identity |
| `/api/v1/authenticate` | POST | Multimodal authentication and fused decision |
| `/api/v1/verify/face` | POST | Face-only verification |
| `/api/v1/verify/voice` | POST | Voice-only verification |
| `/api/v1/health` | GET | Service health and loaded model versions |
| `/api/v1/audit` | GET | Authorized audit-event query |

Application account authentication is separate from biometric identity verification. Proposed protected endpoints use bearer-token authentication; administrator/evaluator permissions are role-based. The health endpoint is proposed as unauthenticated.

## 9. Decision and safety requirements

- Identity scores and authenticity scores are separate signals; do not conflate them.
- A face match does not establish liveness or absence of manipulation.
- A speaker match does not establish that audio is live or non-synthetic.
- A detector result is evidence, not proof.
- Missing, invalid, low-quality, conflicting, or failed signals must be represented explicitly.
- Timeouts and model failures return explicit errors or a conservative Step-up/Block outcome according to a documented policy. Never default to Allow.
- Fusion thresholds must be selected on validation data, not the final test set.
- Preserve the modality-specific results so evaluators can compare them with the fused decision.
- Reason codes must be stable, non-sensitive, and understandable.

## 10. Non-functional requirements and proposed targets

| Area | Requirement / target | Measurement |
|---|---|---|
| Latency | Proposed p95 ≤ 2 seconds for a defined local test configuration and small controlled gallery | Repeated requests; disclose hardware, input duration, gallery size, and timing boundaries |
| Reliability | No failure silently returns Allow | Failure injection and integration tests |
| Security | No secrets in source control; resolve critical security issues before demo | Secret/dependency scans and access tests |
| Privacy | Consent, minimum necessary data, defined retention and deletion | Storage/log review |
| Maintainability | Pinned dependencies and reproducible builds/experiments | Clean setup test |
| Accessibility | Keyboard controls, readable labels, sufficient contrast | Manual checklist |

The latency figure is a proposed target, not a measured result. Do not publish performance claims until measured.

## 11. Data and privacy requirements

Core proposed entities:
- `UserIdentity`: pseudonymous internal identity ID and consent status.
- `BiometricReference`: reference ID, modality (`face` or `voice`), embedding/model version, protected storage reference.
- `AuthenticationEvent`: event ID, decision, reason codes, latency.
- `EvaluationRun`: run ID, dataset split, metrics/configuration references.
- Additional proposed diagram entities include `ModelVersion` and `MetricResult`; exact schema/relationships remain to be finalized.

Privacy rules:
- Treat face images, voice recordings, and embeddings as sensitive biometric data.
- Prefer compliant public datasets and synthetic/pseudonymous test identities.
- Use volunteers only where necessary and only with informed consent and required approval.
- Define retention with the project guide before collecting volunteer data.
- Provide deletion on request and document vector-index deletion/rebuild behavior.
- Restrict access and encrypt transfers/storage where supported.
- Do not commit biometric samples, embeddings, secrets, or restricted datasets to Git.
- Do not log raw audio/video, full embeddings, passwords, or unnecessary identifying information.
- Raw media should be transient by default unless retention is explicitly approved.

## 12. Evaluation and success metrics

Evaluate tasks independently before fusion.

- **Face identity:** ROC/DET, FAR, FRR, and threshold-based results on held-out data.
- **Face PAD:** APCER/BPCER or dataset-appropriate metrics for labeled attack types.
- **Face manipulation:** per-class precision, recall, F1, confusion matrix where labels support them.
- **Speaker verification:** EER/ROC-AUC or dataset-appropriate metrics.
- **Audio anti-spoof:** metrics appropriate to the selected labeled dataset and supported attack classes.
- **Fusion:** compare against face-only and voice-only baselines; target a measurable improvement in at least one preselected security metric without unacceptable FRR/latency degradation.
- **Latency:** repeated measurements with hardware, batch size, gallery size, and input duration disclosed.
- **Reliability:** documented end-to-end tests and failure cases.

Keep identities/sessions separated across splits where applicable. Record dataset license, counts, class balance, preprocessing, model versions, thresholds, environment, and random seeds where applicable. Report limitations and confidence intervals where feasible.

## 13. Milestones

The synopsis proposes a provisional 10-week plan through mid-December; actual university dates and review milestones must be confirmed.

1. Requirements, literature review, dataset/license review, risk register.
2. Architecture, data plan, API contracts, development environment.
3. Face baseline and gallery search.
4. Face security evaluation (PAD and manipulation).
5. Voice baseline and audio anti-spoof feasibility/evaluation.
6. Calibration and fusion experiments.
7. API/database integration and audit events.
8. UI integration and modality comparison view.
9. End-to-end, security, reliability, and latency testing.
10. Final hardening, evaluation report, demo, and submission.

A staged face-only baseline is the fallback if schedule, data, or compute constraints threaten delivery.

## 14. Out-of-scope / unresolved decisions

Do not invent final answers for these:
- Final datasets, model architectures, checkpoints, versions, and licenses.
- Final score thresholds and fusion weights/policy.
- Exact API schemas and authentication implementation.
- Final database schema and migrations.
- FAISS versus Qdrant final choice (FAISS is the initial local-prototype option).
- Raw media retention duration and volunteer-data approval.
- Final hardware, gallery size, and latency measurement setup.
- Final numerical success thresholds beyond proposed targets.
- Calendar dates, guide approval, backup/recovery objectives.

Track these as decisions/TBDs in the repository.
