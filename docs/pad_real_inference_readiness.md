# PAD Real-Inference Readiness Audit

Status: **ready for a separately authorized artifact; real inference has not
been run**.

This audit covers the Open Model Zoo `anti-spoof-mn3` adapter and its
per-face integration. It does not authorize, download, convert, or execute a
model artifact.

## Current artifact contract

| Item | Required contract |
|---|---|
| Filename | `anti-spoof-mn3.onnx` |
| Default location | `models/liveness/anti-spoof-mn3.onnx` |
| Explicit override | `backend\realtime_demo.py --pad-model <path>` |
| Input | One BGR face crop from the existing SCRFD bounding box |
| Input tensor | `[1, 3, 128, 128]`, `float32`, NCHW |
| Resize | 128x128, OpenCV `INTER_LINEAR` |
| Color order | BGR for the converted OMZ artifact |
| Normalization | `(pixel - mean) / scale` |
| Mean | `[151.2405, 119.5950, 107.8395]` |
| Scale | `[63.0105, 56.4570, 55.0035]` |
| Output | `[1, 2]`, floating point |
| Class 0 | Real / bona fide |
| Class 1 | Spoof / attack |
| Default output interpretation | Probabilities |
| Optional interpretation | Logits only when explicitly configured; stable softmax is applied once |

The adapter validates the number of inputs and outputs, tensor shapes, and
floating-point metadata before retaining the ONNX Runtime session. Inference
also validates output shape, finiteness, probability range, and probability
sum. A malformed model is unavailable at load time or an error at inference
time; it cannot produce a bona-fide result.

The adapter reports the providers returned by the actual session. The
preferred provider order is `CUDAExecutionProvider` followed by
`CPUExecutionProvider`. Provider availability alone is not evidence that a
particular inference executed on CUDA. A future real run must record the
session provider and, if GPU claims matter, collect ONNX Runtime profiling
evidence.

## Authorization checklist

| Question | Current status | Required evidence before acquisition |
|---|---|---|
| Original source code license | MIT was identified for `kprokofi/light-weight-face-anti-spoofing` | Preserve the exact source revision and license notice |
| OMZ repository/metadata license | Apache 2.0 repository metadata | Preserve the exact OMZ revision and notices |
| Pretrained checkpoint license | **NOT CLEARED** | Written terms covering the exact artifact and intended use |
| CelebA-Spoof dataset terms | **NOT CLEARED for this artifact/use** | Maintainer/dataset terms and restrictions reviewed |
| Academic/educational use | Not assumed | Explicit evidence that this project’s use is permitted |
| Redistribution | Not assumed | Written permission or terms allowing the planned storage/distribution |
| Commercial use | Not assumed/permitted | Separate commercial clearance if applicable |
| ONNX conversion/derivative artifact | Not independently established | Artifact provenance and conversion/derivative permissions |
| Artifact integrity | No local artifact | SHA-256 calculated after authorized acquisition |

Source-code and repository licenses do not automatically license pretrained
weights or data-derived artifacts. The model remains **NOT CLEARED** until
the checkpoint, dataset terms, intended-use scope, and derivative/redistribution
rights are explicitly documented.

## SHA-256 verification procedure

After authorization and acquisition from the documented source, keep the
artifact outside Git and run:

```powershell
Get-FileHash 'D:\AuthorizedModels\anti-spoof-mn3.onnx' -Algorithm SHA256
```

Record the resulting SHA-256, source URL, source revision, acquisition date,
file size, and license/provenance decision in a local or approved audit record.
Do not treat the previously recorded OMZ digest as a SHA-256 value; the prior
audit identified it as a 128-character digest apparently representing
SHA-512. Recompute SHA-256 locally.

## Runtime behavior

### Recognition-only mode

If the default artifact is absent, the webcam demo continues with ArcFace
recognition and reports PAD as `unavailable`. No PAD score is synthesized.
An explicit `--pad-model` path that does not exist has the same safe behavior
when it is the default path; an explicitly supplied path that exists but
fails loading is reported as a PAD model error and does not silently fall
back to a different model.

### Recognition plus PAD mode

When an authorized, valid artifact is supplied, the existing SCRFD result is
used exactly once. Each detected face gets an independent clipped crop and
anti-spoof inference. ArcFace identity and PAD authenticity are separate
signals and separate fields.

An unset PAD threshold returns `uncertain` with raw scores but no final
threshold decision. A threshold must be selected on development/validation
data, never on the final test set. Inference, crop, metadata, or output
failures return `error`; missing model/session setup returns `unavailable`.
Neither state becomes bona fide.

PAD refreshes are configurable through `RealtimeConfig.pad_refresh_interval`.
When a PAD refresh is skipped, the current result does not display prior PAD
scores as if they were current.

## Safety checks completed with controlled doubles

The mocked tests verify:

- BGR preprocessing, shape, dtype, normalization, and invalid input handling.
- Input/output metadata mismatch rejection.
- Probability output validation and one-time logits softmax.
- NaN, infinity, malformed shape, and invalid probability rejection.
- Missing model and session initialization failures.
- CPU/CUDA provider reporting using controlled sessions.
- Non-negative inference timing.
- Recognition-only behavior with missing PAD.
- Known and unknown identities independently paired with bona fide/attack PAD.
- PAD failure without interrupting identity output.
- Identity failure without suppressing an independent PAD result.
- Multiple faces and independent track results.
- Track expiration.
- Unset threshold producing `uncertain`.
- Invalid adapter scores producing `error` with no displayed scores.

These are contract and integration tests using synthetic images, embeddings,
and controlled adapters. They are **not real model inference**, accuracy
measurements, GPU measurements, or PAD benchmarks.

## Real-inference execution checklist

Only after authorization:

1. Acquire the exact documented `anti-spoof-mn3.onnx` artifact from an
   approved source; do not substitute another model.
2. Record source URL, OMZ/source revisions, license evidence, file size, and
   SHA-256.
3. Store the artifact outside Git, preferably under the ignored local model
   directory or an approved model store.
4. Confirm the adapter loads and prints the expected input/output metadata.
5. Confirm the actual session provider list. Test CPU explicitly if a CPU
   baseline is needed.
6. Run a small authorized smoke test with consented/synthetic inputs without
   logging raw media or embeddings.
7. Record inference latency and provider/profile evidence; do not infer GPU
   execution from `get_available_providers()`.
8. Compare observed metadata and output interpretation with the documented
   contract before accepting scores.
9. Select PAD thresholds and uncertainty margins on a development/validation
   protocol only.
10. Run subject/session-disjoint evaluation with authorized data and report
    APCER, BPCER, ACER, coverage, exclusions, and any supported attack-class
    limitations.
11. Keep identity and PAD metrics separate; do not turn a PAD score into an
    identity decision.
12. Update the registry and audit record with measured evidence. Do not claim
    real PAD support until these steps pass.

## Files audited

- `backend/app/face/liveness/antispoof_mn3.py`
- `backend/app/face/liveness/orchestrator.py`
- `backend/app/face/liveness/config.py`
- `backend/realtime/face_pipeline.py`
- `backend/realtime/realtime_recognition.py`
- `backend/realtime_demo.py`
- `backend/tests/test_antispoof_mn3.py`
- `backend/tests/test_face_pipeline_integration.py`
- `evaluation/experiments/face_pad/README.md`
- `docs/model_registry.md`
- `models/liveness/` (contains only `.gitkeep`)
