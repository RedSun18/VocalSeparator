"""
models/model_manager.py — Downloads, caches, and verifies pretrained separation models.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Demucs will auto-download and cache models here
_DEFAULT_CACHE = Path.home() / "Library" / "Application Support" / "VocalSeparator" / "models"

# Supported model configurations
MODEL_INFO = {
    "htdemucs_ft": {
        "display": "Hybrid Demucs v4 (Fine-tuned)",
        "description": "Best quality. Fine-tuned on vocals. Slower.",
        "stems": ["vocals", "drums", "bass", "other"],
    },
    "htdemucs": {
        "display": "Hybrid Demucs v4",
        "description": "High quality. Good balance of speed and accuracy.",
        "stems": ["vocals", "drums", "bass", "other"],
    },
    "mdx_extra": {
        "display": "MDX-Net Extra",
        "description": "Fast MDX-Net model with extra training data.",
        "stems": ["vocals", "no_vocals"],
    },
    "mdx_extra_q": {
        "display": "MDX-Net Extra Q",
        "description": "MDX-Net quantised — fastest option.",
        "stems": ["vocals", "no_vocals"],
    },
}


class ModelManager:
    """
    Manages AI model lifecycle:
    - Ensures cache directory exists
    - Provides model metadata
    - Triggers demucs auto-download on first use
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or _DEFAULT_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Tell demucs / torch hub where to store files
        os.environ.setdefault("TORCH_HOME", str(self.cache_dir / "torch"))
        os.environ.setdefault("DEMUCS_HOME", str(self.cache_dir))

    def get_cache_dir(self) -> Path:
        return self.cache_dir

    def model_display_name(self, model_key: str) -> str:
        return MODEL_INFO.get(model_key, {}).get("display", model_key)

    def model_stems(self, model_key: str) -> list:
        return MODEL_INFO.get(model_key, {}).get("stems", ["vocals", "other"])

    def is_mdx_model(self, model_key: str) -> bool:
        return model_key.startswith("mdx")

    def available_models(self) -> dict:
        return {k: v["display"] for k, v in MODEL_INFO.items()}
