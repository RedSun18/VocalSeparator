"""
utils/helpers.py — Utility functions used across the application.
"""

import os
import tempfile
from pathlib import Path


def format_duration(seconds: float) -> str:
    """Convert float seconds to mm:ss or hh:mm:ss string."""
    if seconds <= 0:
        return "0:00"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"


def format_filesize(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 0:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_output_dir() -> str:
    """
    Return the directory where separated stems are saved.
    Uses ~/Music/VocalSeparator/outputs, falls back to a temp dir.
    """
    preferred = Path.home() / "Music" / "VocalSeparator" / "outputs"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return str(preferred)
    except OSError:
        return tempfile.mkdtemp(prefix="vocalsep_")


def sanitize_filename(name: str) -> str:
    """Remove characters unsafe for filenames."""
    unsafe = r'\/:*?"<>|'
    for ch in unsafe:
        name = name.replace(ch, "_")
    return name.strip("._")
