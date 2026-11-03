"""Run a local, two-image ArcFace verification demonstration.

This script performs real inference and never prints or persists embeddings.
"""

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

try:
    from app.face.recognition import ArcFaceEngine, FaceVerifier
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.face.recognition import ArcFaceEngine, FaceVerifier
    from backend.app.core.config import settings


def run_verification(engine, verifier, image_a: Path, image_b: Path):
    """Extract each image once and verify the resulting embeddings."""
    embedding_a = engine.extract_from_path(str(image_a))
    embedding_b = engine.extract_from_path(str(image_b))
    result = verifier.verify_embeddings(embedding_a.embedding, embedding_b.embedding)
    return embedding_a, embedding_b, result


def main() -> int:
    parser = argparse.ArgumentParser(description="TrueFace AI-X ArcFace demo")
    parser.add_argument("image_a", type=Path)
    parser.add_argument("image_b", type=Path)
    args = parser.parse_args()

    engine = ArcFaceEngine()
    engine.load_model()
    verifier = FaceVerifier(engine=engine)
    embedding_a, embedding_b, result = run_verification(
        engine, verifier, args.image_a, args.image_b
    )

    print("TRUEFACE AI-X - ARCFACE TEST")
    print(f"\nModel: {result.model_name}")
    print(f"Execution providers: {', '.join(engine.active_providers)}")
    print(f"\nImage A: Successfully loaded ({embedding_a.embedding.size} dimensions)")
    print(f"Image B: Successfully loaded ({embedding_b.embedding.size} dimensions)")
    print(f"\nCosine Similarity: {result.similarity:.6f}")
    print(f"Threshold: {result.threshold:.6f} (configured placeholder)")
    print(f"Verification: {'MATCH' if result.is_match else 'NO MATCH'}")
    pair_time_ms = embedding_a.inference_time_ms + embedding_b.inference_time_ms
    print(f"\nImage A extraction: {embedding_a.inference_time_ms:.2f} ms")
    print(f"Image B extraction: {embedding_b.inference_time_ms:.2f} ms")
    print(f"Pair extraction time: {pair_time_ms:.2f} ms")
    print("Similarity and decision time is excluded from extraction timings.")
    print(f"Configured threshold: {settings.FACE_MATCH_THRESHOLD:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
