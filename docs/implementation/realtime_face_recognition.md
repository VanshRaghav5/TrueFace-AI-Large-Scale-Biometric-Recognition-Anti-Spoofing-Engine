# Real-time face recognition prototype

This milestone adds a standalone webcam prototype. It is not integrated with
FastAPI, the frontend, the voice pipeline, the fusion policy, or the database.
It supports recognition-only operation and an optional, independent
anti-spoof-mn3 branch when an authorized ONNX artifact is supplied.

## Architecture

```text
OpenCV camera -> ArcFaceEngine/SCRFD (one detection pass)
              -> per-face identity branch -> IdentityGallery
              -> optional per-face anti-spoof-mn3 branch
              -> independent identity/authenticity overlay
```

The existing `ArcFaceEngine` and its `buffalo_l` model pack are reused. The
gallery stores normalized 512-dimensional templates only in process memory.
Each identity may have multiple templates; matching compares the probe with
every template and uses that identity's highest similarity. This is simple and
explainable, but it can be sensitive to template quality and does not replace
validation-based threshold calibration.

## Enrollment from `Trueface_Dataset`

The demo uses this repository-local folder by default:

```text
D:\Projects\Personal Projects\TrueFaceAI\Trueface_Dataset
```

For a flat folder, files must use the naming convention
`identity_<sample>.<extension>`. For example, `person_a_1.jpg` and
`person_a_2.jpg` are enrolled as `Person A`. Subfolders are also supported;
the relative subfolder path is used as the identity ID.

Run directly against the folder:

```powershell
cd 'D:\Projects\Personal Projects\TrueFaceAI'
python backend\realtime_demo.py --consent-confirmed
```

The default path is resolved from the repository location, so the command
continues to work if the repository is moved to another drive or directory.

To select another folder:

```powershell
python backend\realtime_demo.py `
  --dataset-dir 'D:\TrueFace-TestData' `
  --consent-confirmed
```

The folder is scanned before the camera opens. Every image must contain
exactly one detectable face. Failed images are reported and are not converted
into matches.

## PAD runtime modes

Recognition-only mode is the default when
`models\liveness\anti-spoof-mn3.onnx` is absent:

```powershell
python backend\realtime_demo.py --consent-confirmed
```

When an authorized artifact is available, pass it explicitly. The adapter
reuses the existing SCRFD boxes, reports real/spoof scores only after actual
inference, and does not substitute test predictions:

```powershell
python backend\realtime_demo.py `
  --pad-model 'D:\AuthorizedModels\anti-spoof-mn3.onnx' `
  --pad-threshold 0.75 `
  --consent-confirmed
```

The threshold must be selected on a validation/development dataset; omission
leaves the PAD result `uncertain` rather than making an access decision.
Identity similarity and PAD authenticity remain separate signals.

## Optional enrollment manifest

Create a manifest outside the repository, for example
`D:\TrueFace-TestData\enrollment.json`:

```json
{
  "identities": [
    {
      "id": "person_a",
      "name": "Person A",
      "images": [
        "D:\\TrueFace-TestData\\person_a_1.jpg",
        "D:\\TrueFace-TestData\\person_a_2.jpg"
      ]
    }
  ]
}
```

Enrollment requires explicit consent on the command line. Every enrollment
image must contain exactly one detectable face. Failed images are reported and
are not converted into matches. If all images for an identity fail, startup
stops.

## Run on Windows PowerShell

From the repository root:

```powershell
cd 'D:\Projects\Personal Projects\TrueFaceAI'
python backend\realtime_demo.py `
  --manifest 'D:\TrueFace-TestData\enrollment.json' `
  --consent-confirmed
```

Use `--camera-index 1` for another camera and configure the uncalibrated demo
threshold explicitly with `--threshold 0.75`. The threshold is not a
production-validated value.

The application requests 640x480 capture by default, initializes the model
once, and keeps the camera open only while the demo runs. Recognition is
refreshed periodically for tracked boxes; it is not permanently bound to a
track. Press `Q` to quit, `R` to refresh visible faces, and `H` to print help.

## Runtime and performance

The overlay reports measured FPS, per-face track IDs, identity similarity, and
per-face recognition processing latency. It also reports whether the loaded
engine reports `CUDAExecutionProvider` as active. It does not claim that every
operation runs on CUDA. For provider-level evidence, use the
existing opt-in ONNX Runtime profiling support in `ArcFaceEngine`.

The engine returns the embedding produced during the same
`FaceAnalysis.get()` call as detection. The realtime layer reuses that
embedding instead of running the detector a second time on a tight bounding-box
crop. This avoids false `No face detected` results caused by recropping and
avoids duplicate recognition inference.

## Recognition stability and tracking

The realtime layer uses IoU association with expiring temporary track IDs.
Each track keeps its current box, last recognition frame, recent raw gallery
results, candidate identity, and confirmation count. A new identity is not
displayed after one strong frame: it must meet the configurable
`confirmation_frames` count. A weak result or an `Unknown` result clears the
candidate and displayed identity. Expired tracks cannot retain old identity
labels.

This is temporal display stabilization, not additional biometric evidence.
Repeated weak evidence does not become a match because only gallery results
that individually meet the configured threshold can advance confirmation.

## Benchmarking

Run a measured camera benchmark with local enrollment data:

```powershell
python backend\realtime\benchmark.py `
  --dataset-dir 'D:\Projects\Personal Projects\TrueFaceAI\Trueface_Dataset' `
  --duration 60
```

The benchmark reports measured FPS, frame-processing latency, recognition
latency for detected faces, model initialization time, provider configuration,
and enrollment counts. It does not claim GPU memory usage unless a separate
measured probe is added. A three-person demo gallery is not a formal accuracy
benchmark; unknown rejection requires a separate consented non-enrolled sample.
Use `--report path\to\report.json` to save the measured JSON output. The
current camera benchmark records the timing scope explicitly and does not
silently remove warm-up frames.

The GPU benchmark recorded on 2026-11-03 is stored at
`evaluation/reports/arcface_gpu_2026-11-03.json`. It used an RTX 3050 Laptop
GPU with CUDA and CPU providers available, 2 enrolled identities and 3
templates, and measured 25.711 average FPS, 36.578 ms average frame
processing, 42.006 ms p95 frame processing, and 2,763.505 ms initialization.
These are measurements for that camera session, not accuracy or PAD results.

## Privacy and limitations

- Enrollment images must remain outside Git and require consent.
- Templates exist only in memory and are not written to disk.
- Frames are not saved and embeddings are not logged.
- A failed extraction is shown as `Unknown` for display and logged only as a
  warning without embedding contents.
- `Unknown` means the best similarity did not meet the configured threshold;
  it does not prove that the person is absent from the gallery.
- A photograph or replayed screen can be recognized because this milestone has
  no liveness or presentation-attack detection.
- Do not use this prototype for access control or other high-impact decisions.

## Troubleshooting

- **Model unavailable:** install the existing backend requirements and exactly
  one ONNX Runtime distribution, then verify the `buffalo_l` model can load.
- **Enrollment failed:** check that each path exists, is readable, and contains
  exactly one face.
- **Camera unavailable:** check Windows camera privacy permissions, close other
  camera applications, and try another `--camera-index`.
- **CPU/fallback shown:** inspect the active provider list and ONNX Runtime
  profile; provider availability alone is not proof of GPU execution.

## PAD preparation and integration status

The per-face integration displays track ID, identity/Unknown, identity
similarity, PAD state, optional real/spoof scores, branch latencies, total
latency, and active providers. Missing PAD weights produce `unavailable`;
inference and input failures produce `error`. A bona-fide PAD result never
implies a known identity, and a known identity never implies bona-fide
presentation.

The PAD package contains a generic ONNX adapter and a separate,
checkpoint-independent MiniFASNet ensemble adapter. The selected upstream
ensemble consists of:

- `2.7_80x80_MiniFASNetV2.pth`
- `4_0_0_80x80_MiniFASNetV1SE.pth`

The upstream inference contract uses two 80x80 BGR crops expanded by scales
2.7 and 4.0. NumPy inputs are converted to float32 NCHW without division by
255. Each branch produces three class logits, class index 1 is the
bona-fide class, and the two class-1 probabilities are averaged.

The checkpoint-specific license remains unresolved. No checkpoints or
datasets are stored in this repository, and ONNX conversion and numerical
compatibility are unproven. MiniFASNet tests use synthetic images, bounding
boxes, and mocked outputs only; they are not real PAD evaluation.

The separate anti-spoof-mn3 adapter uses the OMZ 128x128 BGR contract and
model-specific mean/scale normalization. Its artifact remains **NOT CLEARED**:
no weights have been downloaded or executed, and the integration tests use
controlled adapters only.
