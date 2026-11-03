# Face PAD evaluation

This directory contains the offline evaluation contract for face
presentation-attack detection. It does not contain datasets or model weights.

## Current implementation status

The repository includes an explicit-state ONNX adapter in
`backend/app/face/liveness/onnx_pad.py`. It requires a model-specific ONNX
file and a documented output contract. No PAD weights are currently stored in
`models/liveness/`, so real PAD inference and PAD metrics are not reported.

The separate `antispoof_mn3.py` adapter prepares the Open Model Zoo
anti-spoof-mn3 contract without downloading or loading the artifact. It
expects a converted-model BGR crop, resizes to 128x128, applies
`(pixel - mean) / scale` with mean
`[151.2405, 119.5950, 107.8395]` and scale
`[63.0105, 56.4570, 55.0035]`, and validates one `[1, 2]` output. Class 0 is
real and class 1 is spoof. The default output mode is probabilities; logits
must be selected explicitly and are softmaxed once. Metadata and actual
session providers are checked at load time.

The adapter returns one of:

- `bona_fide`: evaluated score is at or above the configured threshold.
- `attack`: evaluated score is below the threshold.
- `uncertain`: score is within the configured uncertainty margin.
- `unavailable`: weights are missing or the model cannot be loaded.
- `error`: input, output, or inference failure.

`bona_fide_score` means the model's probability of the bona-fide class. It is
not an identity score and is not proof that a person is live.

## MiniFASNet preparation contract

The selected technical baseline is the upstream two-branch ensemble:

- `2.7_80x80_MiniFASNetV2.pth`
- `4_0_0_80x80_MiniFASNetV1SE.pth`

At upstream revision
`b6d5f04ad78778917853b25c778acef6d5626d15`, each branch consumes one
80x80x3 BGR crop. The crops use scales 2.7 and 4.0 around the existing face
bounding box. The upstream NumPy-to-tensor path converts HWC to float32 NCHW
without dividing by 255. Each branch returns three logits; softmax is applied
per branch, class index 1 is treated as bona fide, and the branch scores are
averaged.

The upstream source repository is Apache 2.0 licensed, but the
checkpoint-specific license and redistribution terms are unresolved. No
checkpoints are present in `models/liveness/`. The project has not performed
ONNX conversion, numerical comparison, real inference, or accuracy
evaluation. The MiniFASNet tests are mocked contract tests only.

The application boundary converts missing weights to `unavailable` and
technical PAD failures to `error`. Only a valid, thresholded model result may
be `bona_fide`. The MiniFASNet adapter intentionally has no default decision
threshold or uncertainty margin; those must be selected on validation data.

## anti-spoof-mn3 clearance status

The candidate artifact is `anti-spoof-mn3.onnx` from Open Model Zoo revision
`af810de42bcf460a18610481f639dcdc86249e69`, with the OMZ-recorded checksum
available in the prior provenance report. The artifact has **NOT CLEARED**
status for this project: no file has been acquired, independently hashed, or
run. The original source and OMZ metadata licenses do not by themselves
resolve restrictions associated with CelebA-Spoof-derived pretrained weights.
The anti-spoof-mn3 tests use controlled fake sessions only.

## Dataset research

- **Replay-Attack**: 1,300 clips from 50 clients, with train/development/test
  and enrollment partitions and client-disjoint splits. The official page
  documents print and replayed-screen attacks under controlled and adverse
  lighting: https://www.idiap.ch/en/dataset/replay-attack
- **CASIA-FASD**: a commonly used research face anti-spoofing dataset. Obtain
  it only from the official institution/source and verify its current access
  terms before use; no copy is redistributed here.
- **CelebA-Spoof**: a large-scale face anti-spoofing dataset with attack
  annotations. Access, license, and protocol must be checked from the
  maintainers before download; no copy is redistributed here.

Evaluation must preserve subject/session separation. Thresholds must be
selected on development/validation data only and reported separately from the
final test set. Reports must include total samples, valid bona-fide and attack
predictions, unavailable/error/uncertain/invalid samples, unsupported labels,
missing scores, protocol/manifest exclusions, and coverage percentage. The
evaluation is not marked valid until exclusions are reviewed and official
protocol counts reconcile; no numerical minimum coverage requirement is
selected before a pilot and protocol review. Coverage is based only on the
single metric-valid set: records with a usable finite score and supported
ground-truth label. Protocol exclusions may overlap state categories and are
reported separately rather than added as independent totals.

## Candidate baselines

1. **MiniFASNet/Silent-Face-Anti-Spoofing**: compact, approximately 80x80
   input, suitable for a 4 GB GPU. The upstream project publishes code and
   model resources, but its license, weight provenance, preprocessing, and
   camera-domain limitations must be reviewed before adoption:
   https://github.com/minivision-ai/Silent-Face-Anti-Spoofing
2. **DeepPixBiS-style patch supervision**: a compact spatial anti-spoofing
   baseline that can be exported to ONNX, but requires a reproducible
   implementation, licensed weights, and a defined training/evaluation
   protocol before use.

MiniFASNet is the recommended first baseline for a later approval because it
has a small input and model footprint. It is not selected as an evaluated
model yet because no approved weights are present.
