# Face recognition implementation

## Scope

The independent face-recognition component uses InsightFace's `buffalo_l`
pack. Its pipeline includes SCRFD face detection, five-point landmarks and the
ArcFace recognition model. It returns an internal 512-dimensional,
L2-normalized embedding and supports 1:1 cosine-similarity verification.

Identity similarity is separate from liveness and manipulation detection. This
component does not claim that a matching face is live or genuine.

## Model and licensing

The model pack is downloaded by InsightFace on first load and is not stored in
Git. InsightFace documents `buffalo_l` as subject to its model-license terms;
review the current [model-zoo license](https://github.com/deepinsight/insightface/tree/master/model_zoo)
and obtain any required permission before non-research use. The project makes
no commercial licensing claim.

## Installation and GPU verification

Install the shared requirements, then install exactly one ONNX Runtime variant
in the selected backend environment. The shared requirements intentionally do
not install either runtime distribution:

```powershell
# GPU installation
python -m pip install -r backend\requirements.txt
python -m pip install "insightface>=0.7.3"
python -m pip uninstall -y onnxruntime
python -m pip install "onnxruntime-gpu>=1.17.3"

# CPU-only installation
python -m pip install -r backend\requirements.txt
python -m pip install "insightface>=0.7.3"
python -m pip install "onnxruntime>=1.17.3"
```

Do not install `onnxruntime` and `onnxruntime-gpu` together. If switching
variants, uninstall the current distribution first:

```powershell
python -m pip uninstall -y onnxruntime onnxruntime-gpu
```

InsightFace's model package is compatible with either runtime variant because
both provide the `onnxruntime` Python module. Verify the selected runtime with:

```powershell
python -c "import onnxruntime as ort; print(ort.__version__); print(ort.get_available_providers())"
```

`CUDAExecutionProvider` must be present for GPU inference. The engine exposes
`active_providers` and `is_gpu_active`; provider availability alone is not a
benchmark or proof that every operation ran on the GPU.

## Usage

```python
from backend.app.face.recognition import ArcFaceEngine, FaceVerifier

engine = ArcFaceEngine()
engine.load_model()
verifier = FaceVerifier(engine=engine)
result = verifier.verify_images("reference.jpg", "probe.jpg")
```

Invalid images, no-face images, multiple faces, unavailable models, malformed
embeddings, and inference failures raise explicit errors. Multiple faces are
rejected by default; callers must opt into `allow_multiple=True`.

The threshold from `FACE_MATCH_THRESHOLD` is an initial configuration value,
not a validated production threshold. Threshold selection belongs to a
validation split and must not use the final test set.

The detector threshold is configured with `ArcFaceEngine(det_thresh=...)`,
validated to `[0.0, 1.0]`, and passed to InsightFace's SCRFD `prepare` call.

## Testing and demonstration

Run model-independent tests with:

```powershell
pytest backend/tests/test_arcface_engine.py
```

Run real local inference from the backend directory:

```powershell
python test_arcface.py path\to\image_a.jpg path\to\image_b.jpg
```

This requires InsightFace, a downloaded model pack, and a compatible ONNX
Runtime installation. The demonstration prints scores and timing only; it
does not print or persist embeddings.

ONNX Runtime profiling is opt-in:

```python
engine = ArcFaceEngine(
    enable_profiling=True,
    profiling_dir=r"D:\TrueFace-Profiles",
)
engine.load_model()
engine.detect_faces(image)
profile_paths = engine.end_profiling()
print(profile_paths)
```

Call `end_profiling()` after the measured inference. It finalizes one JSON
profile per loaded InsightFace session. The profile's node events include the
provider where available, allowing CUDA execution and CPU fallback operations
to be inspected. Profiling is disabled by default.

## Evaluation status and limitations

The evaluation scaffold under
`evaluation/experiments/face_recognition/` records validation-only threshold
selection and the required metrics. LFW, CFP-FP, and AgeDB are not downloaded
or measured in this repository. Dataset access, licensing, identity leakage,
split definitions, model version, and environment must be recorded before
reporting results.

The current FastAPI face endpoint remains a mock integration surface by design.
Replacing it with real inference requires a separate integration change that
adds upload limits, timeout handling, authorization, and explicit modality
error states.

Aligned-face diagnostics are opt-in and write only derived 112x112 crops to a
caller-selected local directory:

```python
engine = ArcFaceEngine(diagnostic_dir=r"D:\TrueFace-Diagnostics")
result = engine.extract_from_path(
    r"D:\Trueface_Dataset\person_a_1.jpg",
)
print(result.aligned_face_path)
```

The crop uses InsightFace's `face_align.norm_crop` with the detected five-point
landmarks, matching the alignment used by the ArcFace recognizer. Do not point
the diagnostic directory at the repository, and delete derived crops when the
investigation is complete.
