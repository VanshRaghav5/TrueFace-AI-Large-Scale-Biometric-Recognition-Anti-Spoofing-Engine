# TrueFace AI-X — Agent and Automation Rules

**Purpose:** Define how Claude Code and any AI-assisted development workflows should work in this repository, and define the runtime boundaries of the project's model-processing components.

> **Important architecture distinction:** The synopsis describes deterministic ML pipelines and a fusion/risk engine. It does **not** specify autonomous LLM agents, an agent framework, or an LLM-powered authentication decision-maker. Do not introduce autonomous agents into the biometric decision path. In this document, “agent” can mean either (a) Claude Code as a development assistant, or (b) a bounded model/service component. These are not interchangeable.

---

## 1. Mission

Help the team implement TrueFace AI-X as a safe, explainable, reproducible academic prototype for:
- Face identity verification/search.
- Face liveness / presentation-attack detection.
- Face manipulation detection.
- Speaker verification.
- Audio replay/synthetic-speech anti-spoofing.
- Score calibration and multimodal fusion/risk decisions.
- FastAPI, PostgreSQL/vector search, and a Next.js dashboard.
- Evaluation, testing, and documentation.

Do not expand the product beyond the approved synopsis without asking for an explicit decision.

## 2. Non-negotiable project rules

1. **Read before changing:** Inspect the existing repository, relevant docs, dependency files, and tests before editing.
2. **Synopsis is the source of truth:** Preserve the defined scope, goals, roles, and limitations in the approved synopsis and these project docs.
3. **No invented implementation status:** Do not claim a model, endpoint, dataset, metric, or feature exists until verified in code or measured.
4. **No fabricated metrics:** Never invent accuracy, FAR/FRR, EER, APCER/BPCER, ROC-AUC, latency, or benchmark results.
5. **No silent Allow:** Missing input, low quality, conflicting evidence, timeout, unavailable model, invalid output, or internal failure must never silently become Allow.
6. **Separate identity and authenticity:** A face/speaker match is not proof of liveness or genuineness.
7. **No detector is proof:** Describe detector outputs as model evidence for supported conditions, not certainty.
8. **Privacy by default:** No raw biometric media, full embeddings, secrets, or restricted datasets in Git or ordinary logs.
9. **Consent first:** Enrollment requires consent and authorization.
10. **Validation-only threshold selection:** Never tune thresholds on the final test set.
11. **Reproducibility:** Record dataset split, model version/hash, threshold, environment, and seed where applicable.
12. **Small, reviewable changes:** Avoid unrelated refactors and new infrastructure without a demonstrated need.

## 3. Claude Code operating procedure

For every task:

1. Summarize the requested change and identify affected modules.
2. Inspect the repository tree and relevant source files.
3. Check existing conventions, dependencies, tests, and API contracts.
4. State assumptions and unresolved choices before making a consequential architectural change.
5. Implement the smallest coherent change.
6. Add or update tests.
7. Run relevant tests, lint/type checks, and report exact commands/results.
8. Review the diff for accidental secrets, data files, unrelated edits, and unsafe fallback behavior.
9. Update documentation when contracts, setup, configuration, or behavior changes.
10. Report what changed, what was tested, and what remains unverified.

If a requirement is ambiguous and the choice changes security, privacy, model behavior, API compatibility, data retention, or architecture, ask the user instead of guessing.

## 4. Tool and permission boundaries

Claude Code may use repository tools and shell commands that are available in its environment, subject to user/project permissions.

- Prefer read-only inspection before writes.
- Do not run destructive commands, delete data, reset databases, rewrite Git history, or overwrite user work without explicit approval.
- Do not install new packages or download large model/dataset artifacts without checking the existing environment and explaining the need.
- Do not send biometric samples, embeddings, credentials, or private project files to external services.
- Do not access external services or datasets in ways that violate their terms.
- Do not commit, push, publish, deploy, or change production resources unless explicitly requested.
- Do not expose `.env`, tokens, private keys, database credentials, or personal biometric data in output.
- Use `.env.example` with placeholders; keep real values in ignored local configuration.
- If a tool/action is unavailable, state the limitation; do not pretend it ran.

## 5. Runtime model-component contracts

These are bounded software components, not autonomous agents. They must not call arbitrary tools, browse the internet, modify records, or make policy decisions outside their defined interface.

### 5.1 Face pipeline component
Input: validated face image/clip and optional claimed identity/reference context.

Responsibilities:
- Decode and validate supported media.
- Detect and align faces.
- Check quality and report failure states.
- Generate versioned face embeddings.
- Perform 1:1 verification or controlled-gallery 1:N search.
- Run configured PAD/liveness and manipulation models.
- Return typed identity and authenticity outputs separately.

Must not:
- Enroll an identity without the authorized enrollment workflow.
- Convert low-quality/failed detection into a positive match.
- Claim unsupported attack coverage.
- Return raw embeddings to the browser.

### 5.2 Voice pipeline component
Input: validated audio and optional claimed identity/reference context.

Responsibilities:
- Validate format, duration, and sample conditions.
- Run VAD and preprocessing.
- Generate speaker embeddings and verify against an enrolled reference.
- Run configured audio anti-spoofing for supported attack classes.
- Return typed identity and authenticity outputs separately.

Must not:
- Treat speaker similarity as proof of live speech.
- Treat unsupported audio conditions as verified genuine.
- Return raw embeddings to the browser.

### 5.3 Vector-search component
Responsibilities:
- Store/search permitted reference vectors.
- Map index identifiers to pseudonymous internal identity IDs.
- Enforce controlled-gallery boundaries.
- Support documented deletion and rebuild procedures.

Must not:
- Expose unrestricted gallery contents.
- Treat nearest-neighbor retrieval alone as a final authentication decision.
- Lose the mapping between index IDs and internal identities.

### 5.4 Fusion/risk component
Input: typed face and voice results, including explicit missing/error states and calibrated scores.

Responsibilities:
- Validate signal availability and schema.
- Apply documented calibration and decision policy.
- Return `allow`, `step_up`, or `block` plus stable reason codes.
- Preserve modality-specific results for audit/evaluation.
- Record policy/model version.

Must not:
- Use an LLM to improvise the authentication decision.
- Treat a missing score as zero or as a positive result.
- Default to Allow on exceptions, timeouts, or malformed outputs.
- Hide modality conflicts.
- Tune thresholds on test data.
- claim a detector proves identity or authenticity.

### 5.5 API/orchestration component
Responsibilities:
- Application authentication and role-based authorization.
- Input validation and safe file handling.
- Bounded model orchestration and timeout handling.
- Call the fusion/risk component.
- Persist minimal audit events.
- Return typed, explicit responses.

Must not:
- Trust frontend role flags.
- Log raw media or full embeddings.
- Leak stack traces or secrets.
- turn service/model failure into HTTP success with an Allow decision.

## 6. Required result-state vocabulary

Represent modality status explicitly. Suggested normalized states:

- `available`
- `missing`
- `invalid`
- `low_quality`
- `unsupported`
- `timeout`
- `model_unavailable`
- `error`

The exact enum and API schema must be finalized in code, but do not collapse these states into a single boolean.

Overall decisions:
- `allow`
- `step_up`
- `block`
- `error` (for request/system failure where a decision cannot safely be made)

Do not equate `error` with `block` in UI or analytics.

## 7. Reason-code behavior

Reason codes should be:
- Stable and version-controlled.
- Machine-readable.
- Mapped to safe, understandable UI copy.
- Non-sensitive; do not include raw input, secrets, or personal data.
- Specific enough to distinguish identity mismatch, authenticity risk, missing modality, quality failure, timeout, and model/service error.

Examples are illustrative only; the team must finalize the actual enum:
- `FACE_IDENTITY_MISMATCH`
- `FACE_QUALITY_LOW`
- `FACE_PAD_RISK`
- `FACE_MANIPULATION_RISK`
- `VOICE_IDENTITY_MISMATCH`
- `AUDIO_QUALITY_LOW`
- `AUDIO_SPOOF_RISK`
- `MODALITY_MISSING`
- `MODEL_TIMEOUT`
- `MODEL_UNAVAILABLE`
- `SIGNAL_CONFLICT`

Do not emit a reason code unless its condition is actually evaluated and supported.

## 8. Evaluation-agent / experiment-script rules

Evaluation scripts may automate repeatable model testing, but must:
- Use explicit dataset manifests and splits.
- Verify dataset license/access conditions before use.
- Prevent identity/session leakage where applicable.
- Keep train, validation, and test roles separate.
- Select thresholds on validation data only.
- Evaluate face, voice, PAD, manipulation, and audio anti-spoof tasks separately before fusion.
- Compare face-only, voice-only, and fused modes.
- Save configuration, model version/hash, environment, random seed, and dataset metadata.
- Report failure cases and supported attack classes.
- Never overwrite prior reports without an explicit instruction.
- Clearly label synthetic/demo fixtures and unmeasured targets.

## 9. Privacy and security rules

- Obtain informed consent and required approvals before volunteer data collection.
- Prefer compliant public research datasets and pseudonymous/synthetic test identities.
- Store minimum necessary metadata.
- Keep raw media transient by default.
- Define retention with the guide before collecting volunteer samples.
- Provide deletion on request and document vector-index deletion/rebuild.
- Restrict reference and audit access.
- Encrypt transfers/storage where supported.
- Never commit biometric data, embeddings, or secrets.
- Never include raw media or full embeddings in application logs, error reports, or test snapshots.
- Use synthetic fixtures for unit tests wherever possible.

## 10. Coding and dependency rules

- Follow the repository's established language, formatting, and naming conventions.
- Prefer typed interfaces and explicit schemas for model results.
- Keep model loading separate from per-request inference.
- Make model paths and thresholds configurable; do not scatter magic numbers.
- Pin dependencies and document model/dataset licenses.
- Add timeouts and explicit exception handling around inference.
- Avoid heavyweight new services unless justified.
- Keep model and dataset artifacts outside Git by default.
- Ensure local setup can be reproduced from documented steps.

## 11. Testing checklist for AI-assisted changes

Before declaring a task complete, verify the relevant items:

- [ ] Valid input path works.
- [ ] Invalid format/size/duration is rejected clearly.
- [ ] Missing modality is represented explicitly.
- [ ] Low-quality input does not become a positive result.
- [ ] Model timeout/unavailability is handled safely.
- [ ] Fusion handles genuine, mismatch, spoof, missing, and conflicting signals.
- [ ] No failure path returns Allow.
- [ ] Authorization is enforced server-side.
- [ ] Raw media/embeddings/secrets are absent from logs and Git diff.
- [ ] Tests use controlled fixtures and do not depend on private biometric data.
- [ ] Evaluation thresholds are not selected using the final test set.
- [ ] Documentation and API contracts match the implementation.

## 12. Communication format for Claude Code

At the end of a task, report:

1. **Implemented:** concise list of files and behavior changed.
2. **Design decisions:** choices made and why; list unresolved decisions separately.
3. **Validation:** exact tests/commands run and pass/fail outcomes.
4. **Risks / limitations:** untested paths, model/data dependencies, or known limitations.
5. **Next step:** one concrete next action.

Never say “fully secure,” “100% accurate,” “deepfake-proof,” or “production-ready” based only on a successful local test.
