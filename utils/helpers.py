"""
utils/helpers.py
Utility functions for VocalSeparator.
"""

import os
import sys
import tempfile
from pathlib import Path


def format_duration(seconds: float) -> str:
    """Format seconds as mm:ss string."""
    if seconds <= 0:
        return "0:00"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def format_filesize(size_bytes: int) -> str:
    """Format file size as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_output_dir() -> str:
    """Get or create the output directory for separated stems."""
    if sys.platform == "win32":
        # Try Music folder first, fall back to Documents
        music = Path.home() / "Music"
        docs  = Path.home() / "Documents"
        base  = music if music.exists() else docs
        preferred = base / "VocalSeparator" / "outputs"
    else:
        preferred = Path.home() / "Music" / "VocalSeparator" / "outputs"

    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return str(preferred)
    except OSError:
        return tempfile.mkdtemp(prefix="vocalsep_")
