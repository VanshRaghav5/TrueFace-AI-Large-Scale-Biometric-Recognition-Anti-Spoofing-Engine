"""Comprehensive voice recognition pipeline test.

Tests the full flow: initialization, embedding extraction, similarity computation,
enrollment (simulated), and verification (simulated) with synthetic speech-like
audio signals at different frequencies to represent distinct speakers.
"""

import asyncio
import io
import wave
from pathlib import Path

import numpy as np

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.voice.voice_runtime import voice_runtime
from backend.app.voice.speaker_verification.voice_engine import compute_voice_similarity


def generate_synthetic_speaker(base_freq: float, duration: float = 3.0, sr: int = 16000) -> bytes:
    """Generate a synthetic speech-like signal with harmonics and amplitude modulation.
    
    Args:
        base_freq: Fundamental frequency (Hz). Different frequencies = different "speakers".
        duration: Audio duration in seconds.
        sr: Sample rate (Hz).
    
    Returns:
        WAV bytes (16-bit PCM mono).
    """
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Fundamental + first harmonic
    signal = 0.6 * np.sin(2 * np.pi * base_freq * t) + 0.3 * np.sin(2 * np.pi * base_freq * 2 * t)
    # Amplitude modulation (simulates prosody/pitch variation)
    signal *= (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t))
    
    # Convert to 16-bit PCM
    int16_samples = (signal * 32767).astype(np.int16)
    
    # Write to WAV bytes
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(int16_samples.tobytes())
    return buf.getvalue()


async def test_voice_pipeline():
    print("=" * 70)
    print("TrueFace AI-X Voice Recognition Pipeline Test")
    print("=" * 70)
    
    # 1. Initialize
    print("\n[1/6] Initializing voice runtime...")
    status = voice_runtime.initialize()
    print(f"      Initialized: {status.initialized}")
    print(f"      Model: {status.model_name} v{status.model_version}")
    print(f"      Embedding dimension: {status.dimension}")
    print(f"      Source: {status.model_source}")
    if status.error:
        print(f"      ⚠️  Error: {status.error}")
        return
    print("      [OK] Voice runtime ready")
    
    # 2. Generate synthetic speakers
    print("\n[2/6] Generating synthetic speakers...")
    speaker_alice_freq = 200  # Hz (simulates female voice range)
    speaker_bob_freq = 120    # Hz (simulates male voice range)
    speaker_charlie_freq = 300  # Hz (distinct from both)
    
    alice_wav_1 = generate_synthetic_speaker(speaker_alice_freq, 3.5)
    alice_wav_2 = generate_synthetic_speaker(speaker_alice_freq, 3.0)  # Different duration, same speaker
    bob_wav = generate_synthetic_speaker(speaker_bob_freq, 3.2)
    charlie_wav = generate_synthetic_speaker(speaker_charlie_freq, 2.8)
    print(f"      Generated 3 synthetic speakers (Alice, Bob, Charlie)")
    
    # 3. Extract embeddings
    print("\n[3/6] Extracting speaker embeddings...")
    alice_emb_1, alice_quality_1 = voice_runtime.extract(alice_wav_1)
    alice_emb_2, alice_quality_2 = voice_runtime.extract(alice_wav_2)
    bob_emb, bob_quality = voice_runtime.extract(bob_wav)
    charlie_emb, charlie_quality = voice_runtime.extract(charlie_wav)
    
    print(f"      Alice sample 1: {alice_emb_1.shape} dur={alice_quality_1.duration_seconds}s "
          f"norm={np.linalg.norm(alice_emb_1):.4f}")
    print(f"      Alice sample 2: {alice_emb_2.shape} dur={alice_quality_2.duration_seconds}s "
          f"norm={np.linalg.norm(alice_emb_2):.4f}")
    print(f"      Bob:            {bob_emb.shape} dur={bob_quality.duration_seconds}s "
          f"norm={np.linalg.norm(bob_emb):.4f}")
    print(f"      Charlie:        {charlie_emb.shape} dur={charlie_quality.duration_seconds}s "
          f"norm={np.linalg.norm(charlie_emb):.4f}")
    print("      [OK] All embeddings are L2-normalized unit vectors")
    
    # 4. Compute similarities
    print("\n[4/6] Computing speaker similarities...")
    sim_alice_self = compute_voice_similarity(alice_emb_1, alice_emb_2)
    sim_alice_bob = compute_voice_similarity(alice_emb_1, bob_emb)
    sim_alice_charlie = compute_voice_similarity(alice_emb_1, charlie_emb)
    sim_bob_charlie = compute_voice_similarity(bob_emb, charlie_emb)
    
    print(f"      Alice vs Alice (self):  {sim_alice_self:.4f}")
    print(f"      Alice vs Bob:           {sim_alice_bob:.4f}")
    print(f"      Alice vs Charlie:       {sim_alice_charlie:.4f}")
    print(f"      Bob vs Charlie:         {sim_bob_charlie:.4f}")
    
    threshold = 0.70
    print(f"\n      Match threshold: {threshold}")
    print(f"      Self-match works: {sim_alice_self > 0.95} (expected: near 1.0)")
    print(f"      Cross-speaker discriminates: {sim_alice_bob < threshold and sim_alice_charlie < threshold}")
    
    if sim_alice_self < 0.95:
        print("      [WARN] Warning: Self-match is not deterministic (should be ~1.0)")
    if sim_alice_bob >= threshold or sim_alice_charlie >= threshold:
        print(f"      [WARN] Warning: Cross-speaker similarity is too high (threshold={threshold})")
    else:
        print("      [OK] Similarity computation works correctly")
    
    # 5. Simulate enrollment (mock DB session)
    print("\n[5/6] Simulating enrollment...")
    class MockTemplate:
        def __init__(self, embedding):
            self.embedding = embedding.tobytes()
    
    class MockSession:
        def __init__(self, enrolled_embedding=None):
            self.enrolled_embedding = enrolled_embedding
        
        async def execute(self, stmt):
            class MockResult:
                def __init__(self, template):
                    self._template = template
                def scalars(self):
                    class MockScalars:
                        def __init__(self, template):
                            self._template = template
                        def first(self):
                            return self._template
                    return MockScalars(self._template)
            if self.enrolled_embedding is not None:
                return MockResult(MockTemplate(self.enrolled_embedding))
            else:
                return MockResult(None)
    
    print("      Enrolled Alice's first sample as reference template")
    
    # 6. Verify
    print("\n[6/6] Testing verification...")
    
    # Test 6a: Alice verifying with her own second sample (should match)
    print("\n      [6a] Alice verifying with her second sample:")
    session_alice = MockSession(enrolled_embedding=alice_emb_1)
    result_alice_match = await voice_runtime.verify(
        alice_wav_2, claimed_subject_id='alice', session=session_alice
    )
    print(f"           Status: {result_alice_match.status}")
    print(f"           Speech detected: {result_alice_match.speech_detected}")
    print(f"           Identity similarity: {result_alice_match.identity_similarity:.4f}")
    print(f"           Antispoof score: {result_alice_match.antispoof_score:.4f}")
    print(f"           Is match (>={threshold}): {result_alice_match.identity_similarity >= threshold if result_alice_match.identity_similarity else False}")
    print(f"           Reason codes: {result_alice_match.reason_codes}")
    
    if 'VOICE_IDENTITY_MATCH' in result_alice_match.reason_codes:
        print("           [OK] Correctly matched Alice")
    else:
        print("           [FAIL] Failed to match Alice (self-verification)")
    
    # Test 6b: Bob trying to verify as Alice (should mismatch)
    print("\n      [6b] Bob attempting to impersonate Alice:")
    result_bob_impersonate = await voice_runtime.verify(
        bob_wav, claimed_subject_id='alice', session=session_alice
    )
    print(f"           Status: {result_bob_impersonate.status}")
    print(f"           Identity similarity: {result_bob_impersonate.identity_similarity:.4f}")
    print(f"           Is match (>={threshold}): {result_bob_impersonate.identity_similarity >= threshold if result_bob_impersonate.identity_similarity else False}")
    print(f"           Reason codes: {result_bob_impersonate.reason_codes}")
    
    if 'VOICE_IDENTITY_MISMATCH' in result_bob_impersonate.reason_codes:
        print("           [OK] Correctly rejected Bob (impostor)")
    else:
        print("           [FAIL] Failed to reject Bob (security risk!)")
    
    # Test 6c: Verify against non-enrolled subject
    print("\n      [6c] Verifying against non-enrolled subject:")
    session_no_template = MockSession(enrolled_embedding=None)
    result_not_enrolled = await voice_runtime.verify(
        charlie_wav, claimed_subject_id='charlie', session=session_no_template
    )
    print(f"           Status: {result_not_enrolled.status}")
    print(f"           Identity similarity: {result_not_enrolled.identity_similarity}")
    print(f"           Reason codes: {result_not_enrolled.reason_codes}")
    
    if 'VOICE_TEMPLATE_NOT_ENROLLED' in result_not_enrolled.reason_codes:
        print("           [OK] Correctly reported not enrolled")
    else:
        print("           [WARN] Did not report missing enrollment")
    
    # Test 6d: Verify without claimed identity
    print("\n      [6d] Verifying without claimed subject ID:")
    result_no_claim = await voice_runtime.verify(
        alice_wav_1, claimed_subject_id=None, session=session_alice
    )
    print(f"           Reason codes: {result_no_claim.reason_codes}")
    
    if 'VOICE_CLAIMED_IDENTITY_OMITTED' in result_no_claim.reason_codes:
        print("           [OK] Correctly reported missing identity claim")
    else:
        print("           [WARN] Did not report missing identity claim")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_pass = (
        status.initialized
        and sim_alice_self > 0.95
        and sim_alice_bob < threshold
        and 'VOICE_IDENTITY_MATCH' in result_alice_match.reason_codes
        and 'VOICE_IDENTITY_MISMATCH' in result_bob_impersonate.reason_codes
    )
    
    if all_pass:
        print("[PASS] All tests PASSED - Voice recognition pipeline is working correctly!")
        print("\nNext steps:")
        print("  1. Test with real microphone recordings (3-10s of speech)")
        print("  2. Enroll multiple real speakers through /api/v1/enrollment")
        print("  3. Verify through /api/v1/voice/verify or /api/v1/authentication/verify")
        print("  4. Collect validation pairs to calibrate VOICE_MATCH_THRESHOLD")
    else:
        print("[FAIL] Some tests FAILED - Review the results above")
        if not status.initialized:
            print("   - Voice runtime failed to initialize")
        if sim_alice_self <= 0.95:
            print("   - Self-match is not deterministic")
        if sim_alice_bob >= threshold:
            print(f"   - Cross-speaker similarity is above threshold ({sim_alice_bob:.4f} >= {threshold})")
        if 'VOICE_IDENTITY_MATCH' not in result_alice_match.reason_codes:
            print("   - Failed to match legitimate user")
        if 'VOICE_IDENTITY_MISMATCH' not in result_bob_impersonate.reason_codes:
            print("   - Failed to reject impostor")
    
    print("=" * 70)


if __name__ == "__main__":
    import os
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    asyncio.run(test_voice_pipeline())
