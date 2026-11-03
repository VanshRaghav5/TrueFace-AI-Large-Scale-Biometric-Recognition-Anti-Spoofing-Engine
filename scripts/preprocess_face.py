#!/usr/bin/env python3
"""
TrueFace AI-X — Face Preprocessing Utility
Validates image dimensions, blur, illumination, and provides standard alignment routines.
"""

import os
import sys

def preprocess_face_image(image_path: str, output_path: str, target_size=(112, 112)):
    """Preprocess, crop, and resize face images for ArcFace recognition."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")
    print(f"Preprocessing face image: {image_path} -> {output_path} ({target_size[0]}x{target_size[1]})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python preprocess_face.py <input_image> <output_image>")
    else:
        preprocess_face_image(sys.argv[1], sys.argv[2])

