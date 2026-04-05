"""
audio/loader.py — Audio file validation, metadata, and format conversion.
"""

import os
import subprocess
import json
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif"}


@dataclass
class AudioInfo:
    path: str
    filename: str
    duration: float = 0.0
    sample_rate: int = 44100
    channels: int = 2
    bitrate: int = 0
    format: str = ""
    size_bytes: int = 0

    def __getitem__(self, key):
        """Allow dict-style access: info["duration"], info["size"]."""
        if key == "size":
            return self.size_bytes
        return getattr(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except AttributeError:
            return default


def _find_ffprobe() -> Optional[str]:
    import shutil
    for candidate in ["ffprobe", "/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"]:
        found = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if found:
            return found
    return None


def _find_ffmpeg() -> Optional[str]:
    import shutil
    for candidate in ["ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        found = shutil.which(candidate) or (candidate if os.path.isfile(candidate) else None)
        if found:
            return found
    return None


class AudioLoader:
    def is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def get_info(self, path: str) -> Optional[AudioInfo]:
        path = str(Path(path).resolve())
        info = AudioInfo(
            path=path,
            filename=Path(path).name,
            size_bytes=os.path.getsize(path) if os.path.isfile(path) else 0,
            format=Path(path).suffix.lower().lstrip("."),
        )

        ffprobe = _find_ffprobe()
        if not ffprobe:
            logger.warning("ffprobe not found — returning basic info")
            return info

        try:
            result = subprocess.run(
                [ffprobe, "-v", "quiet", "-print_format", "json",
                 "-show_streams", "-show_format", path],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(result.stdout)

            fmt = data.get("format", {})
            info.duration = float(fmt.get("duration", 0))
            info.bitrate = int(fmt.get("bit_rate", 0)) // 1000

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    info.sample_rate = int(stream.get("sample_rate", 44100))
                    info.channels = int(stream.get("channels", 2))
                    break
        except Exception as e:
            logger.warning(f"ffprobe failed: {e}")

        return info

    def convert_to_wav(self, input_path: str, output_path: str) -> bool:
        ffmpeg = _find_ffmpeg()
        if not ffmpeg:
            logger.error("ffmpeg not found")
            return False
        try:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", input_path,
                 "-ar", "44100", "-ac", "2", "-f", "wav", output_path],
                capture_output=True, timeout=120,
            )
            return result.returncode == 0 and os.path.isfile(output_path)
        except Exception as e:
            logger.error(f"ffmpeg conversion failed: {e}")
            return False
