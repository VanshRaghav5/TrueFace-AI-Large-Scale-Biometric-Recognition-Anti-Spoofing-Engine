#!/usr/bin/env python3
"""
Setup script to download and configure required model files for TrueFace AI-X.
This script creates the directory structure and downloads models from InsightFace.
"""

import os
import sys
from pathlib import Path

def create_model_directories():
    """Create required model directory structure."""
    
    base_dir = Path(__file__).parent.parent
    model_dirs = [
        "models/face/detection",
        "models/face/recognition", 
        "models/liveness",
        "models/deepfake",
        "models/voice/vad",
        "models/voice/speaker_verification",
        "models/voice/anti_spoofing",
    ]
    
    print("Creating model directory structure...")
    for dir_path in model_dirs:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")
    
    print("\n✅ Directory structure created!")

def download_insightface_models():
    """Download InsightFace models using the buffalo_l pack."""
    
    print("\n📦 Downloading InsightFace models...")
    print("This will download the buffalo_l model pack (~500MB)")
    print("Models will be cached in: ~/.insightface/models/buffalo_l/\n")
    
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        # Initialize FaceAnalysis - this downloads models automatically
        app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']
        )
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        print("✅ InsightFace models downloaded successfully!")
        print(f"   Location: {os.path.expanduser('~/.insightface/models/buffalo_l/')}")
        
        return True
        
    except ImportError:
        print("❌ InsightFace not installed. Please run: pip install insightface")
        return False
    except Exception as e:
        print(f"❌ Error downloading models: {e}")
        return False

def download_voice_models():
    """Download SpeechBrain ECAPA-TDNN model."""
    
    print("\n🎤 Downloading Voice Recognition models...")
    
    try:
        import torch
        import torchaudio
        from speechbrain.inference.speaker import EncoderClassifier
        
        base_dir = Path(__file__).parent.parent
        model_path = base_dir / "models/voice/speaker_verification"
        
        print("Downloading ECAPA-TDNN from SpeechBrain (this may take a few minutes)...")
        
        # This downloads the model to the specified directory
        classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(model_path),
            run_opts={"device": "cpu"}
        )
        
        print(f"✅ Voice models downloaded successfully!")
        print(f"   Location: {model_path}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Please install: pip install torch torchaudio speechbrain")
        return False
    except Exception as e:
        print(f"❌ Error downloading voice models: {e}")
        return False

def create_placeholder_files():
    """Create placeholder README files in model directories."""
    
    base_dir = Path(__file__).parent.parent
    
    readme_content = {
        "models/liveness/README.md": """# Liveness Detection Models

Place PAD (Presentation Attack Detection) model files here:
- anti-spoof-mn3.onnx (MiniFASNet)

These models are used for detecting face spoofing attacks.
""",
        "models/deepfake/README.md": """# Deepfake Detection Models

Place deepfake detection model files here:
- deepfake_detector.onnx

These models are used for detecting manipulated/synthetic faces.
""",
        "models/voice/anti_spoofing/README.md": """# Voice Anti-Spoofing Models

Place voice anti-spoofing model files here:
- AASIST.pth (or other anti-spoofing models)

These models are used for detecting synthetic speech and replay attacks.
""",
    }
    
    print("\n📝 Creating README files...")
    for file_path, content in readme_content.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"  ✓ {file_path}")

def print_next_steps():
    """Print instructions for manual model downloads."""
    
    print("\n" + "="*60)
    print("📋 NEXT STEPS")
    print("="*60)
    
    print("\n✅ Automatic Downloads Completed:")
    print("  • Face Detection & Recognition (InsightFace)")
    print("  • Voice Recognition (SpeechBrain)")
    
    print("\n⚠️  Manual Downloads Required:")
    print("\n1. PAD (Liveness) Model:")
    print("   - Download: MiniFASNet model")
    print("   - Place in: models/liveness/anti-spoof-mn3.onnx")
    
    print("\n2. Deepfake Detection Model:")
    print("   - Download: Deepfake detection model")
    print("   - Place in: models/deepfake/deepfake_detector.onnx")
    
    print("\n3. Voice Anti-Spoofing Model (Optional):")
    print("   - Download: AASIST model")
    print("   - Place in: models/voice/anti_spoofing/AASIST.pth")
    
    print("\n" + "="*60)
    print("🚀 After adding models, restart the backend server:")
    print("   cd backend")
    print("   uvicorn app.main:app --reload")
    print("="*60 + "\n")

def main():
    """Main setup function."""
    
    print("="*60)
    print("TrueFace AI-X Model Setup")
    print("="*60 + "\n")
    
    # Step 1: Create directories
    create_model_directories()
    
    # Step 2: Download InsightFace models
    face_success = download_insightface_models()
    
    # Step 3: Download Voice models
    voice_success = download_voice_models()
    
    # Step 4: Create placeholder READMEs
    create_placeholder_files()
    
    # Step 5: Print next steps
    print_next_steps()
    
    # Summary
    print("\n📊 SUMMARY:")
    print(f"  Face Models:  {'✅ Ready' if face_success else '❌ Manual download needed'}")
    print(f"  Voice Models: {'✅ Ready' if voice_success else '❌ Manual download needed'}")
    print("  PAD Models:   ⚠️  Manual download needed")
    print("  Deepfake:     ⚠️  Manual download needed\n")

if __name__ == "__main__":
    main()
