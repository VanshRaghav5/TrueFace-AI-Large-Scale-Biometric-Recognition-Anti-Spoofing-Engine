# Face recognition evaluation

This directory contains the reproducible evaluation pipeline for the ArcFace
module. Dataset files, embedding caches, ROC files, and generated reports are
intentionally not committed.

Thresholds must be selected from a validation split, then applied unchanged to
the held-out test split. Record the dataset manifest, split, model pack,
environment, seed, threshold, and measured latency with every report.

## Supported dataset preparation

The evaluator accepts a normalized directory layout:

```text
dataset-root/
  identity-001/
    image-001.jpg
    image-002.jpg
  identity-002/
    image-001.jpg
```

The immediate parent directory is treated as the identity. Images must remain
outside Git and should be copied or linked only after the dataset's access and
license conditions have been reviewed.

Supported source datasets:

- **LFW**: obtain the original images and, where applicable, the official
  restricted/unrestricted pair protocol from the University of Massachusetts
  LFW site: <http://vis-www.cs.umass.edu/lfw/>.
- **CFP-FP**: request the frontal-profile benchmark from the official CFP
  benchmark site: <https://www.cfpw.io/>. Follow its research-use and
  redistribution restrictions.
- **AgeDB**: request AgeDB through the official iBUG resource page:
  <https://ibug.doc.ic.ac.uk/resources/agedb/>. Follow its access, citation,
  and non-redistribution conditions.

The evaluator does not download, redistribute, or convert these datasets
automatically. If a source uses a protocol file rather than identity folders,
prepare an external normalized copy and record the source protocol, version,
license/access approval, and conversion command in the experiment metadata.

## Running an evaluation

Run from the repository root with a Python environment containing the existing
backend dependencies:

```powershell
python evaluation\experiments\face_recognition\evaluate_arcface.py `
  --dataset D:\datasets\lfw-normalized `
  --dataset-name LFW `
  --output-dir D:\TrueFace-Evaluations\lfw `
  --cache-dir D:\TrueFace-Evaluations\cache
```

The evaluator:

1. Splits identities, not images, into train, validation, and test partitions
   using seed `42` by default.
2. Selects the verification threshold using validation genuine/impostor scores
   only.
3. Applies that threshold once to the held-out test partition.
4. Writes `report.json`, `roc_curve.csv`, and `failures.jsonl`.

The cache and output paths must be outside the repository. Failed detection,
invalid images, multiple faces, and invalid embeddings are recorded explicitly
and excluded from scoring; they are never silently converted into impostor
non-matches. A split must contain enough images for both genuine and impostor
pairs, otherwise evaluation stops with an explicit error.

The report records the dataset manifest hash, identity split, model pack,
embedding dimension, threshold provenance, FAR, FRR, TAR, ROC-AUC, EER,
initialization timing, cold/warm extraction timing, pair scoring timing, and
failure count. GPU memory is not inferred: if a future runner adds a measured
GPU-memory probe, its source must be recorded with the report.

The current configured threshold `0.75` is included only as a comparison
placeholder. It is not selected or validated by this scaffold. No LFW, CFP-FP,
or AgeDB result is claimed until an authorized local dataset is supplied.
