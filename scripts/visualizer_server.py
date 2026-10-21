#!/usr/bin/env python3
"""CLI runner for Punggawa 3D Office Event Stream Gateway."""
import os
import sys

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.port_utils import find_available_port
from config.settings import settings
from server.stream_server import run

if __name__ == "__main__":
    # Check port availability and pass resolved port
    resolved_port = find_available_port(
        preferred_port=settings.STREAM_SERVER_PORT,
        fallback_ports=[8001, 8002, 8003, 8080, 8081, 8888],
        host=settings.STREAM_SERVER_HOST,
    )
    run(port=resolved_port)
