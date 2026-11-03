#!/usr/bin/env python3
"""
TrueFace AI-X — Environment Setup & Verification Script
Verifies system runtime, required dependencies, and directory structure.
"""

import sys
import os
import platform

def check_python_version():
    major, minor = sys.version_info[:2]
    print(f"Python version: {major}.{minor}.{sys.version_info.micro} ({platform.system()})")
    if major < 3 or (major == 3 and minor < 10):
        print("[WARNING] Python 3.10+ is recommended for TrueFace AI-X.")
    else:
        print("[OK] Python version compatible.")

def check_directories():
    required_dirs = [
        "docs",
        "frontend",
        "backend",
        "evaluation",
        "models",
        "scripts",
        "tests",
        "infra"
    ]
    print("\nVerifying project directories:")
    for d in required_dirs:
        exists = os.path.exists(d)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {d}")

def check_cuda():
    print("\nChecking hardware acceleration:")
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU Only"
        print(f"  PyTorch: {torch.__version__} | CUDA Available: {cuda_avail} ({device_name})")
    except ImportError:
        print("  PyTorch not installed in current environment.")

if __name__ == "__main__":
    print("=" * 60)
    print("TrueFace AI-X Environment Verification")
    print("=" * 60)
    check_python_version()
    check_directories()
    check_cuda()
    print("=" * 60)

