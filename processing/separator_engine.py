"""
processing/separator_engine.py
Core AI separation engine.
Uses ONLY torch + demucs + soundfile + numpy. No torchaudio. Bundle-safe.
"""

import os
import gc
import re
import logging
import tempfile
from pathlib import Path

import torch
import numpy as np
import soundfile as sf
from PySide6.QtCore import QObject, Signal

from models.model_manager import ModelManager
from audio.loader import AudioLoader

logger = logging.getLogger(__name__)

# Module-level model cache - avoids reloading on every separation
_model_cache = {}


def _detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_audio(path: str, samplerate: int, channels: int) -> torch.Tensor:
    """
    Load audio using soundfile + resampling via scipy.
    Returns tensor of shape (channels, samples).
    No torchaudio required.
    """
    from scipy.signal import resample_poly
    from math import gcd

    data, sr = sf.read(path, always_2d=True)
    # data shape: (samples, channels)

    # Convert to target channel count
    if data.shape[1] == 1 and channels == 2:
        data = np.concatenate([data, data], axis=1)
    elif data.shape[1] > channels:
        data = data[:, :channels]

    # Resample if needed
    if sr != samplerate:
        g = gcd(sr, samplerate)
        up = samplerate // g
        down = sr // g
        data = resample_poly(data, up, down, axis=0).astype(np.float32)
    else:
        data = data.astype(np.float32)

    # (samples, channels) -> (channels, samples)
    tensor = torch.from_numpy(data.T)
    return tensor


def _save_audio(tensor: torch.Tensor, path: str, samplerate: int) -> None:
    """Save audio tensor to WAV using soundfile. No torchaudio required."""
    wav = tensor.cpu().numpy()
    if wav.ndim == 2:
        wav = wav.T  # (channels, samples) -> (samples, channels)
    sf.write(path, wav, samplerate, subtype="PCM_16")


def _run_demucs(model_name, audio_path, output_dir, device,
                progress_callback=None, status_callback=None):
    """Run demucs separation. Torchaudio-free. Windows-compatible."""

    if status_callback:
        status_callback("Loading AI model...")
    if progress_callback:
        progress_callback(15)

    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    # Use cached model if available - avoids reload on second song
    if model_name not in _model_cache:
        model = get_model(model_name)
        model.eval()
        dev = torch.device(device)
        if hasattr(model, 'models'):
            for m in model.models:
                m.to(dev)
        else:
            model.to(dev)
        _model_cache[model_name] = (model, dev)
        logger.info("Model %s loaded and cached", model_name)
    else:
        model, dev = _model_cache[model_name]
        logger.info("Using cached model %s", model_name)

    if status_callback:
        status_callback("Loading audio file...")
    if progress_callback:
        progress_callback(25)

    wav = _load_audio(audio_path, model.samplerate, model.audio_channels)
    wav = wav.to(dev)

    # Normalize
    ref = wav.mean(0)
    mean = ref.mean()
    std = ref.std() + 1e-8
    wav = (wav - mean) / std

    if status_callback:
        status_callback("Separating stems (this may take a few minutes)...")
    if progress_callback:
        progress_callback(30)

    with torch.inference_mode():
        sources = apply_model(
            model,
            wav[None],
            device=dev,
            progress=False,
            num_workers=4,
            segment=7.0,
            overlap=0.1,
        )[0]

    # Denormalize
    sources = sources * std + mean

    if progress_callback:
        progress_callback(88)
    if status_callback:
        status_callback("Exporting stems...")

    stem_sources = model.sources if hasattr(model, 'sources') else \
                   model.models[0].sources

    try:
        vocals_idx = stem_sources.index("vocals")
    except ValueError:
        raise RuntimeError("'vocals' not in model stems: {}".format(stem_sources))

    vocals_wav = sources[vocals_idx]
    no_vocals_wav = sum(
        sources[i] for i in range(len(stem_sources)) if i != vocals_idx
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename for Windows (remove illegal characters)
    stem_name = Path(audio_path).stem
    stem_name = re.sub(r'[<>:"/\\|?*]', '_', stem_name)

    vocals_path = str(out_dir / (stem_name + "_vocals.wav"))
    instr_path  = str(out_dir / (stem_name + "_instrumental.wav"))

    _save_audio(vocals_wav, vocals_path, model.samplerate)
    _save_audio(no_vocals_wav, instr_path, model.samplerate)

    return vocals_path, instr_path


class SeparatorEngine:
    def __init__(self, model_name="htdemucs_ft", model_manager=None, output_format="wav"):
        self.model_name = model_name
        self.model_manager = model_manager or ModelManager()
        self.output_format = output_format
        self._device = _detect_device()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def separate(self, audio_path, output_dir,
                 progress_callback=None, status_callback=None):

        self._cancelled = False
        audio_path = str(Path(audio_path).resolve())
        output_dir = str(Path(output_dir).resolve())
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Convert non-WAV/FLAC formats to WAV first using ffmpeg
        working_path = audio_path
        tmp_wav = None
        if Path(audio_path).suffix.lower() not in {".wav", ".flac"}:
            if status_callback:
                status_callback("Converting audio format...")
            if progress_callback:
                progress_callback(5)
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav.close()
            loader = AudioLoader()
            if not loader.convert_to_wav(audio_path, tmp_wav.name):
                raise RuntimeError(
                    "Could not convert audio. Make sure ffmpeg is installed.")
            working_path = tmp_wav.name

        try:
            vocals, instrumental = _run_demucs(
                model_name=self.model_name,
                audio_path=working_path,
                output_dir=output_dir,
                device=self._device,
                progress_callback=progress_callback,
                status_callback=status_callback,
            )
        finally:
            if tmp_wav and os.path.exists(tmp_wav.name):
                os.unlink(tmp_wav.name)

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback("Separation complete!")

        return vocals, instrumental


class SeparationWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, engine, audio_path, output_dir):
        super().__init__()
        self._engine = engine
        self._audio_path = audio_path
        self._output_dir = output_dir

    def cancel(self):
        self._engine.cancel()

    def run(self):
        try:
            vocals, instrumental = self._engine.separate(
                audio_path=self._audio_path,
                output_dir=self._output_dir,
                progress_callback=lambda v: self.progress.emit(v),
                status_callback=lambda s: self.status.emit(s),
            )
            self.finished.emit(vocals, instrumental)
        except RuntimeError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            logger.exception("Unexpected error")
            self.error.emit("Unexpected error: " + str(exc))
        finally:
            gc.collect()
