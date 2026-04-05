# 🎙 VocalSeparator

**Professional macOS AI-powered vocal & instrumental stem separator.**

Powered by **Demucs v4** (Meta AI) — the same engine used by professional audio engineers worldwide. Separates any song into clean Vocals and Instrumental tracks in minutes, entirely offline.

---

## ✨ Features

- **State-of-the-art AI** — Hybrid Demucs v4 (htdemucs_ft) for maximum separation quality
- **Multiple models** — Choose between Best Quality, Balanced, or Fast separation
- **Apple Silicon optimised** — Uses Metal (MPS) GPU acceleration on M1/M2/M3 Macs
- **Drag & drop interface** — Drop any audio file to get started
- **Multi-format support** — MP3, WAV, FLAC, M4A, AAC
- **In-app playback** — Preview stems before downloading
- **Flexible export** — WAV (lossless) or MP3 320kbps, with ZIP bundle option
- **Non-blocking UI** — All processing runs in background threads

---

## 🖥 System Requirements

| Item | Minimum | Recommended |
|------|---------|-------------|
| macOS | Ventura 13.0 | Sonoma 14.0+ |
| Python | 3.10 | 3.11+ |
| RAM | 8 GB | 16 GB |
| Storage | 5 GB free | 10 GB free |
| GPU | — | Apple Silicon M-series |

---

## 🚀 Installation

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install ffmpeg

```bash
brew install ffmpeg
```

### 3. Install Python 3.11

```bash
brew install python@3.11
```

### 4. Clone or download this project

```bash
git clone https://github.com/yourname/VocalSeparator.git
cd VocalSeparator
```

### 5. Create a virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 6. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Apple Silicon note:** PyTorch will automatically install the MPS-enabled version via pip.  
> If you need a specific version: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu`

---

## ▶ Running the App

```bash
# Make sure your virtual environment is active
source venv/bin/activate

# Launch VocalSeparator
python main.py
```

### Running in VS Code

1. Open the `VocalSeparator` folder in VS Code
2. Press `⌘ + Shift + P` → **Python: Select Interpreter** → choose `./venv/bin/python`
3. Open `main.py`
4. Press `F5` or click **Run → Start Debugging**

---

## 🎵 Usage

1. **Drop** your audio file onto the upload zone, or click **Browse Files**
2. **Select** your preferred model and output format
3. Click **✦ Separate Stems**
4. Wait for processing (first run downloads the model, ~500 MB)
5. **Preview** vocals and instrumental directly in the app
6. **Download** either stem individually or both as a ZIP

### Model Guide

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| Hybrid Demucs v4 (Fine-tuned) | Slow | ★★★★★ | Final production use |
| Hybrid Demucs v4 | Medium | ★★★★☆ | General use |
| MDX-Net Extra | Fast | ★★★☆☆ | Quick previews |

---

## 📁 Output Files

Separated stems are saved to:

```
~/Music/VocalSeparator/outputs/
  └── songname_vocals.wav
  └── songname_instrumental.wav
```

When downloading both via the app, a ZIP is created:

```
songname_stems.zip
  ├── songname_vocals.wav
  └── songname_instrumental.wav
```

---

## 📦 Model Storage

Models are automatically downloaded on first use and cached at:

```
~/Library/Application Support/VocalSeparator/models/
```

They are **not** re-downloaded on subsequent runs.

---

## 🏗 Project Structure

```
VocalSeparator/
├── main.py                    # Entry point
├── requirements.txt
├── README.md
│
├── gui/
│   ├── __init__.py
│   └── main_window.py         # Main window + all UI widgets
│
├── audio/
│   ├── __init__.py
│   └── loader.py              # File validation & ffprobe metadata
│
├── models/
│   ├── __init__.py
│   └── model_manager.py       # Model cache & metadata
│
├── processing/
│   ├── __init__.py
│   └── separator_engine.py    # Demucs inference engine + Qt worker
│
├── utils/
│   ├── __init__.py
│   └── helpers.py             # Formatting, output dir helpers
│
└── assets/
    └── style.qss              # Dark macOS Qt stylesheet
```

---

## 📦 Packaging as a macOS .app

### Install PyInstaller

```bash
pip install pyinstaller
```

### Build the app

```bash
pyinstaller \
  --name "VocalSeparator" \
  --windowed \
  --icon assets/icon.icns \
  --add-data "assets:assets" \
  --hidden-import demucs \
  --hidden-import torch \
  --hidden-import torchaudio \
  --hidden-import soundfile \
  --hidden-import librosa \
  main.py
```

The output will be in `dist/VocalSeparator.app`.

### Notes on bundling

- The AI models (~500 MB each) are **not** bundled — they download on first run to `~/Library/Application Support/VocalSeparator/models`
- To bundle models, add `--add-data "path/to/models:models"` and update `model_manager.py` to check the bundle path first
- Code-signing for distribution: `codesign --deep --force --sign - dist/VocalSeparator.app`

---

## 🔧 Troubleshooting

### "No module named demucs"
```bash
source venv/bin/activate
pip install demucs
```

### "ffmpeg not found"
```bash
brew install ffmpeg
```

### Slow processing on Intel Mac
This is expected — use the **MDX-Net (Fast)** model for quicker results on CPU.

### Out of memory errors
- Use the **MDX-Net (Fast)** model (lower VRAM usage)
- Close other applications
- Split very long files (>15 min) before processing

### Model download fails
Check your internet connection. Models are hosted by Meta/HuggingFace. Retry by restarting separation.

---

## 🏛 Architecture

```
User Input
    │
    ▼
DropZone / FileInfoCard          ← gui/main_window.py
    │
    ▼
AudioLoader.get_info()           ← audio/loader.py
    │  (metadata validation)
    ▼
SeparatorEngine.separate()       ← processing/separator_engine.py
    │  (runs in QThread via SeparationWorker)
    │
    ├── AudioLoader.convert_to_wav()   (ffmpeg)
    ├── demucs CLI subprocess
    └── copy stems to output dir
    │
    ▼
AudioPlayerBar / Download        ← gui/main_window.py
```

The GUI never blocks — all heavy work runs in a `QThread`. Progress signals update the UI in real time via Qt's signal/slot mechanism.

---

## 📄 License

MIT License. Demucs is © Meta AI, licensed under MIT.
