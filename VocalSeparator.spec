# -*- mode: python ; coding: utf-8 -*-
#
# VocalSeparator_windows.spec
# Windows build spec - run with:
#   pyinstaller VocalSeparator_windows.spec --clean --noconfirm

import os
import shutil
import importlib

# ── Locate ffmpeg ─────────────────────────────────────────────────────────────

def find_bin(name):
    found = shutil.which(name)
    if found:
        return found
    for p in [
        r"C:\ffmpeg\bin\\" + name + ".exe",
        r"C:\Program Files\ffmpeg\bin\\" + name + ".exe",
    ]:
        if os.path.isfile(p):
            return p
    raise Exception(f"{name} not found. Install ffmpeg and add it to PATH.")

ffmpeg_path  = find_bin("ffmpeg")
ffprobe_path = find_bin("ffprobe")
print(f"ffmpeg:  {ffmpeg_path}")
print(f"ffprobe: {ffprobe_path}")

# ── Locate packages ───────────────────────────────────────────────────────────

def pkg_dir(name):
    mod = importlib.import_module(name)
    d = os.path.dirname(mod.__file__)
    print(f"  {name}: {d}")
    return d

print("Locating packages...")
demucs_dir     = pkg_dir("demucs")
torchaudio_dir = pkg_dir("torchaudio")
certifi_file   = importlib.import_module("certifi").where()

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        (ffmpeg_path,  '.'),
        (ffprobe_path, '.'),
    ],
    datas=[
        ('assets',      'assets'),
        ('gui',         'gui'),
        ('audio',       'audio'),
        ('models',      'models'),
        ('processing',  'processing'),
        ('utils',       'utils'),
        (demucs_dir,    'demucs'),
        (torchaudio_dir,'torchaudio'),
        (certifi_file,  '.'),
    ],
    hiddenimports=[
        # demucs
        'demucs',
        'demucs.separate',
        'demucs.pretrained',
        'demucs.apply',
        'demucs.htdemucs',
        'demucs.hdemucs',
        'demucs.states',
        'demucs.spec',
        'demucs.utils',
        'demucs.audio',
        'demucs.transformer',
        'demucs.repo',
        'demucs.svd',
        # torchaudio
        'torchaudio',
        'torchaudio._extension',
        'torchaudio.functional',
        'torchaudio.transforms',
        # audio
        'soundfile',
        'scipy',
        'scipy.signal',
        'scipy.signal._upfirdn',
        'scipy.signal._upfirdn_apply',
        # numerics
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core.numeric',
        'numpy.core.umath',
        'numpy.core._multiarray_umath',
        'numpy.lib',
        'numpy.lib.stride_tricks',
        'numpy.linalg',
        'numpy.fft',
        'numpy.random',
        # demucs deps
        'einops',
        'julius',
        # GUI
        'PySide6',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # ssl / network
        'certifi',
        'ssl',
        'urllib',
        'urllib.request',
    ],
    excludes=[
        'torchvision',
        'torchcodec',
        'cv2',
        'matplotlib',
        'tkinter',
        'IPython',
        'jupyter',
    ],
    hookspath=[],
    runtime_hooks=['fix_ssl.py'],
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='VocalSeparator',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets\\icon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name='VocalSeparator',
)
