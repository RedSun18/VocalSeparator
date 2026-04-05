"""
processing/separator_engine.py
Core AI separation engine using demucs Python API.
Bundle-safe - handles bundle environment correctly.
"""

import os
import sys
import gc
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


def _detect_device() -> str:
    """Return the best available device for inference."""
    try:
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            return "mps"
    except Exception:
        pass
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_audio(path: str, samplerate: int, channels: int):
    from scipy.signal import resample_poly
    from math import gcd

    data, sr = sf.read(path, always_2d=True)

    if data.shape[1] == 1 and channels == 2:
        data = np.concatenate([data, data], axis=1)
    elif data.shape[1] > channels:
        data = data[:, :channels]

    if sr != samplerate:
        g = gcd(sr, samplerate)
        up = samplerate // g
        down = sr // g
        data = resample_poly(data, up, down, axis=0).astype(np.float32)
    else:
        data = data.astype(np.float32)

    tensor = torch.from_numpy(data.T)
    return tensor


def _save_audio(tensor, path: str, samplerate: int) -> None:
    wav = tensor.cpu().numpy()
    if wav.ndim == 2:
        wav = wav.T

    ext = Path(path).suffix.lower()
    if ext == ".mp3":
        # Write temp WAV then encode to MP3 via ffmpeg
        import subprocess, shutil, tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        try:
            sf.write(tmp.name, wav, samplerate, subtype="PCM_16")
            ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
            subprocess.run(
                [ffmpeg, "-y", "-i", tmp.name,
                 "-codec:a", "libmp3lame", "-b:a", "320k",
                 "-ar", str(samplerate), path],
                capture_output=True, check=True,
            )
        finally:
            os.unlink(tmp.name)
    else:
        sf.write(path, wav, samplerate, subtype="PCM_16")


def _run_demucs(model_name, audio_path, output_dir, device, output_format="wav",
                progress_callback=None, status_callback=None):
    if status_callback:
        status_callback("Loading AI model…")
    if progress_callback:
        progress_callback(15)

    logger.info(f"Using device: {device} for model {model_name}")

    # Per-model segment/overlap tuning.
    # Demucs models need larger segments for quality; MDX-Net is faster with smaller ones.
    # overlap=0.1 is the minimum safe value (default is 0.25 which wastes ~25% of compute).
    _model_params = {
        "htdemucs_ft": {"segment": 7.8, "overlap": 0.1},
        "htdemucs":    {"segment": 7.8, "overlap": 0.1},
        "mdx_extra":   {"segment": 3,   "overlap": 0.1},
        "mdx":         {"segment": 3,   "overlap": 0.1},
    }
    params = _model_params.get(model_name, {"segment": 7.8, "overlap": 0.1})

    try:
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Demucs import traceback:\n{tb}")
        raise RuntimeError(f"Failed to import demucs: {e}")

    try:
        model = get_model(model_name)
        model.eval()
    except Exception as e:
        raise RuntimeError(f"Failed to load model '{model_name}': {e}")

    dev = torch.device(device)
    try:
        # BagOfModels (ensembles like htdemucs_ft) wraps multiple sub-models.
        # .to(dev) on the bag itself doesn't always propagate on MPS — move each explicitly.
        model.to(dev)
        if hasattr(model, 'models'):
            for m in model.models:
                m.to(dev)
    except Exception as e:
        logger.warning(f"Could not move model to {device}, falling back to CPU: {e}")
        dev = torch.device("cpu")
        model.to(dev)
        if hasattr(model, 'models'):
            for m in model.models:
                m.to(dev)

    if status_callback:
        status_callback("Loading audio file…")
    if progress_callback:
        progress_callback(25)

    try:
        wav = _load_audio(audio_path, model.samplerate, model.audio_channels)
        wav = wav.to(dev)
    except Exception as e:
        raise RuntimeError(f"Failed to load audio: {e}")

    ref = wav.mean(0)
    mean = ref.mean()
    std = ref.std() + 1e-8
    wav = (wav - mean) / std

    if status_callback:
        status_callback("Separating stems (this may take a few minutes)…")
    if progress_callback:
        progress_callback(30)

    with torch.no_grad():
        # MPS requires float32 — models load as float32 by default so this is fine.
        # num_workers=1 enables the overlap-add worker thread for ~10% speedup.
        sources = apply_model(
            model,
            wav[None],
            device=dev,
            progress=False,
            num_workers=1,
            segment=params["segment"],
            overlap=params["overlap"],
        )[0]

    sources = sources * std + mean

    if progress_callback:
        progress_callback(88)
    if status_callback:
        status_callback("Exporting stems…")

    try:
        if hasattr(model, 'sources'):
            stem_sources = model.sources
        elif hasattr(model, 'models') and hasattr(model.models[0], 'sources'):
            stem_sources = model.models[0].sources
        else:
            raise RuntimeError(f"Model does not have 'sources' attribute")
    except Exception as e:
        raise RuntimeError(f"Failed to get model sources: {e}")

    try:
        vocals_idx = stem_sources.index("vocals")
    except ValueError:
        raise RuntimeError(f"'vocals' not in model stems: {stem_sources}")

    vocals_wav = sources[vocals_idx]
    no_vocals_wav = sum(
        sources[i] for i in range(len(stem_sources)) if i != vocals_idx
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem_name = Path(audio_path).stem
    ext = f".{output_format.lower()}"

    vocals_path = str(out_dir / (stem_name + "_vocals" + ext))
    instr_path  = str(out_dir / (stem_name + "_instrumental" + ext))

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

        stem_name = Path(audio_path).stem

        if status_callback:
            status_callback("Checking audio format…")
        if progress_callback:
            progress_callback(2)

        working_path = audio_path
        tmp_wav = None
        if Path(audio_path).suffix.lower() not in {".wav", ".flac"}:
            if status_callback:
                status_callback("Converting audio format…")
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav.close()
            loader = AudioLoader()
            if not loader.convert_to_wav(audio_path, tmp_wav.name):
                raise RuntimeError(
                    "Could not convert audio file. Make sure ffmpeg is installed.")
            working_path = tmp_wav.name
        if progress_callback:
            progress_callback(8)

        if self._cancelled:
            raise RuntimeError("Separation was cancelled.")

        try:
            vocals, instrumental = _run_demucs(
                model_name=self.model_name,
                audio_path=working_path,
                output_dir=output_dir,
                device=self._device,
                output_format=self.output_format,
                progress_callback=progress_callback,
                status_callback=status_callback,
            )
        finally:
            if tmp_wav and os.path.exists(tmp_wav.name):
                os.unlink(tmp_wav.name)

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback("✓ Separation complete!")

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
