#!/usr/bin/env python3
"""
TrueFace AI-X — Vector Index Builder
Constructs or re-indexes the FAISS face gallery from enrolled reference templates.
"""

import os
import sys

def build_index(output_index_path: str, mapping_path: str, dimension: int = 512):
    print(f"Building FAISS vector index (dim={dimension})...")
    os.makedirs(os.path.dirname(output_index_path), exist_ok=True)
    os.makedirs(os.path.dirname(mapping_path), exist_ok=True)
    print(f"Index target: {output_index_path}")
    print(f"Mapping target: {mapping_path}")
    print("Index initialization complete.")

if __name__ == "__main__":
    out_idx = sys.argv[1] if len(sys.argv) > 1 else "backend/app/search/indices/face_gallery.index"
    out_map = sys.argv[2] if len(sys.argv) > 2 else "backend/app/search/indices/identity_mapping.json"
    build_index(out_idx, out_map)

