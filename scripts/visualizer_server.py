#!/usr/bin/env python3
"""CLI runner for Punggawa 3D Office Event Stream Gateway."""
import os
import sys

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from server.stream_server import run

if __name__ == "__main__":
    run()
