"""Quick diagnostic script to test model loading and status."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.face_runtime import face_runtime
from app.voice.voice_runtime import voice_runtime

def test_models():
    print("=" * 60)
    print("Testing Face Runtime")
    print("=" * 60)
    
    face_status = face_runtime.initialize()
    print(f"Face Initialized: {face_status.initialized}")
    print(f"Face Error: {face_status.error}")
    print(f"Face Model: {face_status.model_name}")
    print(f"Face Providers: {face_status.providers}")
    
    print(f"\nPAD Initialized: {face_status.pad_initialized}")
    print(f"PAD Error: {face_status.pad_error}")
    print(f"PAD Model: {face_status.pad_model_name}")
    print(f"PAD Provider: {face_status.pad_provider}")
    
    print(f"\nDeepfake Initialized: {face_status.deepfake_initialized}")
    print(f"Deepfake Error: {face_status.deepfake_error}")
    print(f"Deepfake Model: {face_status.deepfake_model_name}")
    print(f"Deepfake Provider: {face_status.deepfake_provider}")
    
    print("\n" + "=" * 60)
    print("Testing Voice Runtime")
    print("=" * 60)
    
    voice_status = voice_runtime.initialize()
    print(f"Voice Initialized: {voice_status.initialized}")
    print(f"Voice Error: {voice_status.error}")
    print(f"Voice Model: {voice_status.model_name}")
    print(f"Voice Dimension: {voice_status.dimension}")
    
    print(f"\nVoice Antispoof Initialized: {voice_status.antispoof_initialized}")
    print(f"Voice Antispoof Error: {voice_status.antispoof_error}")
    print(f"Voice Antispoof Model: {voice_status.antispoof_model_name}")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_good = (
        face_status.initialized and
        face_status.pad_initialized and
        face_status.deepfake_initialized and
        voice_status.initialized and
        voice_status.antispoof_initialized
    )
    
    if all_good:
        print("✓ All models loaded successfully!")
    else:
        print("✗ Some models failed to load:")
        if not face_status.initialized:
            print(f"  - Face: {face_status.error}")
        if not face_status.pad_initialized:
            print(f"  - PAD: {face_status.pad_error}")
        if not face_status.deepfake_initialized:
            print(f"  - Deepfake: {face_status.deepfake_error}")
        if not voice_status.initialized:
            print(f"  - Voice: {voice_status.error}")
        if not voice_status.antispoof_initialized:
            print(f"  - Voice Antispoof: {voice_status.antispoof_error}")

if __name__ == "__main__":
    test_models()
