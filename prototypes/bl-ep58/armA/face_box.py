#!/usr/bin/env python3
"""Compatibility entry point for tools/bl_face_box.py; use --help for arguments.

The former fixed 56% transform and early-neck heuristic are no longer suitable
for certifying face clearance. The shared tool records the measurement limits.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.bl_face_box import main

if __name__ == '__main__':
    main()
