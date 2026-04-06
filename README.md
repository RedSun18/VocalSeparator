# 🎙 VocalSeparator

**Professional AI-powered vocal & instrumental stem separator for macOS and Windows.**

Powered by **Demucs v4** (Meta AI) — the same engine used by professional audio engineers worldwide. Separates any song into clean Vocals and Instrumental tracks in minutes, entirely offline after the first run.

---

## ✨ Features

- **State-of-the-art AI** — Hybrid Demucs v4 for maximum separation quality
- **Multiple models** — Choose between Best Quality, Balanced, or Fast separation
- **GPU accelerated** — Apple Silicon (MPS) on Mac, NVIDIA CUDA on Windows
- **Drag & drop interface** — Drop any audio file to get started
- **Multi-format support** — MP3, WAV, FLAC, M4A, AAC
- **In-app playback** — Preview stems before downloading
- **Flexible export** — WAV (lossless) or MP3 320kbps, with ZIP bundle option
- **Non-blocking UI** — All processing runs in background threads
- **Model caching** — Model stays loaded between songs in the same session

---

## 📦 Downloads

| Platform | File | Notes |
|----------|------|-------|
| macOS | `VocalSeparator.dmg` | macOS Ventura 13.0+ |
| Windows | `VocalSeparator_Setup.exe` | Windows 10 64-bit+ |

> **First launch security warning:**
> - **macOS** — Right-click the app → Open → click Open (once only)
> - **Windows** — Click "More info" → "Run anyway" (once only)
>
> This is because the app is not signed with a paid developer certificate. It is completely safe.

---

## 🖥 System Requirements

### macOS

| Item | Minimum | Recommended |
|------|---------|-------------|
| macOS | Ventura 13.0 | Sonoma 14.0+ |
| RAM | 8 GB | 16 GB |
| Storage | 2 GB free | 5 GB free |
| GPU | Any | Apple Silicon M1/M2/M3 (much faster) |
| Internet | First run only | — |

### Windows

| Item | Minimum | Recommended |
|------|---------|-------------|
| Windows | Windows 10 64-bit | Windows 11 |
| RAM | 8 GB | 16 GB |
| Storage | 2 GB free | 5 GB free |
| GPU | Any (CPU fallback) | NVIDIA GPU with CUDA (much faster) |
| Internet | First run only | — |

---

## 🎵 Usage

1. **Drop** your audio file onto the upload zone, or click **Browse Files**
2. **Select** your preferred model and output format
3. Click **✦ Separate Stems**
4. Wait for processing — first run downloads the AI model (~320 MB, one time only)
5. **Preview** vocals and instrumental directly in the app
6. **Download** either stem individually or both as a ZIP

### Model Guide

| Model | Speed (GPU) | Speed (CPU) | Quality | Best For |
|-------|-------------|-------------|---------|----------|
| Hybrid Demucs v4 (Best Quality) | ~30-60 sec | ~5-8 min | ★★★★★ | Final production use |
| Hybrid Demucs (Balanced) | ~15-30 sec | ~2-3 min | ★★★★☆ | Everyday use |
| Hybrid Demucs (Fast) | ~10-20 sec | ~1-2 min | ★★★★☆ | Quick previews |

---

## 📁 Output Files

Separated stems are saved automatically to:

**macOS:**
```
~/Music/VocalSeparator/outputs/
  └── songname_vocals.wav
  └── songname_instrumental.wav
```

**Windows:**
```
C:\Users\YourName\Music\VocalSeparator\outputs\
  └── songname_vocals.wav
  └── songname_instrumental.wav
```

When downloading both via the app, a ZIP is created on your Desktop.

---

## 📦 Model Storage

Models are automatically downloaded on first use and cached at:

**macOS:** `~/Library/Application Support/VocalSeparator/models/`

**Windows:** `C:\Users\YourName\AppData\Local\VocalSeparator\models\`

They are **not** re-downloaded on subsequent runs. Internet is only needed once.

---

## 🔧 Troubleshooting

### App won't open on macOS
Right-click the app → Open → click Open. This only needs to be done once.

### App blocked on Windows
Click "More info" → "Run anyway". This only needs to be done once.

### Slow processing
- Make sure you're using the GPU-accelerated version for your platform
- Use the **Balanced** or **Fast** model for quicker results
- Close other heavy applications to free up RAM

### Model download fails on first run
Check your internet connection. Models are hosted by Meta/HuggingFace. Simply restart the app and try again — the download resumes automatically.

### Out of memory errors
- Switch to the **Fast** model (lower memory usage)
- Close other applications
- For very long files (15+ min), consider splitting them first

### No sound in playback
Make sure your system audio output is set correctly. The app uses your default audio device.

---

## 🏗 Project Structure

```
VocalSeparator/
├── main.py                    # Entry point
├── requirements.txt
├── README.md
├── VocalSeparator.spec            # macOS PyInstaller spec
├── VocalSeparator_windows.spec    # Windows PyInstaller spec
├── fix_ssl.py                     # SSL certificate runtime hook
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
    ├── icon.icns              # macOS app icon
    ├── icon.ico               # Windows app icon
    └── style.qss              # Dark Qt stylesheet
```

---

## 🔨 Building from Source

### macOS

```bash
# Install dependencies
brew install ffmpeg
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller VocalSeparator.spec --clean --noconfirm
codesign --deep --force --sign - dist/VocalSeparator.app

# Package as DMG
create-dmg --volname "VocalSeparator" --window-pos 200 120 --window-size 600 400 \
  --icon-size 120 --icon "VocalSeparator.app" 175 190 \
  --hide-extension "VocalSeparator.app" --app-drop-link 425 190 \
  "dist/VocalSeparator.dmg" "dist/VocalSeparator.app"
```

### Windows

```powershell
# Requires Python 3.12 and CUDA toolkit for GPU support

# Create venv
py -3.12 -m venv .venv312
.venv312\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
.venv312\Scripts\python.exe -m pip install demucs soundfile scipy PySide6 pyinstaller certifi numpy

# Build
.venv312\Scripts\python.exe -m PyInstaller VocalSeparator_windows.spec --clean --noconfirm
```

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
    │  (metadata + format validation)
    ▼
SeparatorEngine.separate()       ← processing/separator_engine.py
    │  (runs in QThread via SeparationWorker)
    │
    ├── AudioLoader.convert_to_wav()   (ffmpeg)
    ├── Demucs get_model() + apply_model()
    └── soundfile stem export
    │
    ▼
AudioPlayerBar / Download        ← gui/main_window.py
```

The GUI never blocks — all heavy work runs in a `QThread`. Progress and status signals update the UI in real time via Qt's signal/slot mechanism.

---

## 📄 License

MIT License. Demucs is © Meta AI, licensed under MIT.
