"""
Common filesystem, mathematical modeling, and hashing utilities.
"""

import hashlib
from pathlib import Path
from typing import Optional


def calculate_file_hash(file_path: Path, block_size: int = 65536) -> Optional[str]:
    """
    Computes the SHA256 signature of a target filesystem target incrementally.
    Safely captures unreadable files or unexpected execution context issues.
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except (OSError, PermissionError):
        return None


def format_size(bytes_size: int) -> str:
    """Formats raw numerical bytes into highly readable storage scale strings."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"