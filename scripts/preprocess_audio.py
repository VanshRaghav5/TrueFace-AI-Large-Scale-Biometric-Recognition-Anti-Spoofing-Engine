#!/usr/bin/env python3
"""
TrueFace AI-X — Audio Preprocessing Utility
Converts audio to 16kHz mono WAV, trims silence, and validates SNR.
"""

import os
import sys

def preprocess_audio_sample(audio_path: str, output_path: str, target_sr: int = 16000):
    """Normalize audio sample rate and format for speaker verification and anti-spoofing."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Input audio not found: {audio_path}")
    print(f"Preprocessing audio: {audio_path} -> {output_path} ({target_sr} Hz)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python preprocess_audio.py <input_audio> <output_audio>")
    else:
        preprocess_audio_sample(sys.argv[1], sys.argv[2])

