"""Network and Port Utilities for Punggawa Ecosystem."""
import logging
import socket
from typing import Iterable, Sequence

logger = logging.getLogger("PunggawaPortUtils")


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Check whether a given port is already in use (bound) on the system.
    
    Tries binding to the address using a test TCP socket.
    Returns True if the port is busy, False if it is free to use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(
    preferred_port: int,
    fallback_ports: Sequence[int] = (8001, 8002, 8003, 8080, 8081, 8888),
    host: str = "0.0.0.0",
) -> int:
    """Find an available port without overwriting or conflicting with an occupied port.
    
    1. Checks preferred_port first.
    2. If occupied, checks fallback_ports in order.
    3. If all fallbacks are occupied, automatically finds any available OS port.
    """
    if not is_port_in_use(preferred_port, host=host):
        return preferred_port

    logger.warning(
        f"⚠️  Port {preferred_port} sedang digunakan oleh proses lain! Mencari port alternatif..."
    )

    for fallback in fallback_ports:
        if fallback != preferred_port and not is_port_in_use(fallback, host=host):
            logger.info(f"✅ Port alternatif ditemukan dan akan digunakan: {fallback}")
            return fallback

    # Fallback jika semua daftar port terisi: biarkan OS memilih port dinamis yang bebas
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        dynamic_port = s.getsockname()[1]

    logger.warning(f"⚠️  Semua port default terisi. Menggunakan port dinamis bebas: {dynamic_port}")
    return dynamic_port
