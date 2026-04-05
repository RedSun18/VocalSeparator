# -*- mode: python ; coding: utf-8 -*-
#
# VocalSeparator.spec — fixed for macOS user-install (no venv)
#
# All packages live in:
#   /Users/macbook/Library/Python/3.12/lib/python/site-packages/
# NOT in the system framework site-packages. We import each package
# directly to get its real path instead of relying on sysconfig.

import os
import sys
import glob
import shutil
import importlib

# ── Locate binaries ──────────────────────────────────────────────────────────

def find_bin(name):
    found = shutil.which(name)
    if found:
        return found
    for p in [f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"]:
        if os.path.isfile(p):
            return p
    raise Exception(f"{name} not found. Install with: brew install ffmpeg")

ffmpeg_path  = find_bin("ffmpeg")
ffprobe_path = find_bin("ffprobe")
print(f"ffmpeg:  {ffmpeg_path}")
print(f"ffprobe: {ffprobe_path}")

# ── Find packages by importing them (works regardless of install location) ───

def pkg_dir(name):
    mod = importlib.import_module(name)
    d = os.path.dirname(mod.__file__)
    print(f"  {name}: {d}")
    return d

print("Locating packages...")
ta_root    = pkg_dir("torchaudio")
torch_root = pkg_dir("torch")
demucs_dir = pkg_dir("demucs")

# User site-packages root (one level up from torchaudio)
user_site = os.path.dirname(ta_root)
print(f"user site-packages: {user_site}")

# ── torchaudio native libs — must land FLAT in Frameworks/ ───────────────────

ta_binaries = []
for pattern in ("**/*.so", "**/*.dylib"):
    for fpath in glob.glob(os.path.join(ta_root, pattern), recursive=True):
        ta_binaries.append((fpath, "."))
print(f"torchaudio binaries: {len(ta_binaries)}")

# ── torch native libs ────────────────────────────────────────────────────────

torch_binaries = []
for pattern in ("lib/*.dylib", "lib/*.so"):
    for fpath in glob.glob(os.path.join(torch_root, pattern)):
        torch_binaries.append((fpath, "."))
print(f"torch binaries: {len(torch_binaries)}")

# ── soundfile native lib ─────────────────────────────────────────────────────

sf_binaries = []
for fpath in glob.glob(os.path.join(user_site, "_soundfile*.so")):
    sf_binaries.append((fpath, "."))
for fpath in glob.glob(os.path.join(user_site, "soundfile*", "*.so")):
    sf_binaries.append((fpath, "."))
for fpath in glob.glob(os.path.join(user_site, "soundfile*", "*.dylib")):
    sf_binaries.append((fpath, "."))
print(f"soundfile binaries: {len(sf_binaries)}")

# ── Homebrew audio libs ───────────────────────────────────────────────────────

hb_libs = [
    "libsox.dylib", "libsox.3.dylib",
    "libmpg123.dylib", "libmpg123.0.dylib",
    "libopusfile.dylib", "libopusfile.0.dylib",
    "libvorbisfile.dylib", "libvorbisfile.3.dylib",
    "libFLAC.dylib", "libFLAC.12.dylib",
    "libsndfile.dylib", "libsndfile.1.dylib",
]
hb_binaries = []
for lib in hb_libs:
    for prefix in ["/opt/homebrew/lib", "/usr/local/lib"]:
        p = os.path.join(prefix, lib)
        if os.path.isfile(p):
            hb_binaries.append((p, "."))
            break
print(f"homebrew binaries: {len(hb_binaries)}")

# ── Analysis ─────────────────────────────────────────────────────────────────

a = Analysis(
    ['main.py'],
    pathex=['.', user_site],
    binaries=[
        (ffmpeg_path,  '.'),
        (ffprobe_path, '.'),
    ] + ta_binaries + torch_binaries + sf_binaries + hb_binaries,
    datas=[
        ('assets',     'assets'),
        ('gui',        'gui'),
        ('audio',      'audio'),
        ('models',     'models'),
        ('processing', 'processing'),
        ('utils',      'utils'),
        (demucs_dir,   'demucs'),
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
        'demucs.model',
        'demucs.svd',
        # torchaudio
        'torchaudio',
        'torchaudio._extension',
        'torchaudio._backend',
        'torchaudio.backend',
        'torchaudio.backend.utils',
        'torchaudio.functional',
        'torchaudio.transforms',
        'torchaudio.io',
        # torch — MPS must be explicitly listed or it won't be found in frozen app
        'torch',
        'torch.nn',
        'torch.nn.functional',
        'torch.backends.mps',
        'torch.backends.mps._ops',
        # audio
        'soundfile',
        'scipy',
        'scipy.signal',
        'scipy.signal._upfirdn',
        'scipy.signal._upfirdn_apply',
        'librosa',
        'librosa.core',
        'audioread',
        'pydub',
        # demucs deps
        'einops',
        'julius',
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core._multiarray_umath',
        # GUI
        'PySide6',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # network/ssl
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
        'notebook',
    ],
    hookspath=[],
    runtime_hooks=['fix_ssl.py', 'fix_dylib.py'],
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='VocalSeparator',
    icon='assets/icon.icns',
    debug=False, strip=False, upx=False, console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name='VocalSeparator',
)

app = BUNDLE(
    coll,
    name='VocalSeparator.app',
    icon='assets/icon.icns',
    bundle_identifier='com.vocalseparator.app',
    info_plist={
        'NSPrincipalClass':             'NSApplication',
        'CFBundleName':                 'VocalSeparator',
        'CFBundleDisplayName':          'VocalSeparator',
        'CFBundleVersion':              '1.0.0',
        'CFBundleShortVersionString':   '1.0.0',
        'NSHighResolutionCapable':      True,
        'LSMinimumSystemVersion':       '13.0',
        'NSMicrophoneUsageDescription': 'VocalSeparator needs audio access for playback.',
    },
)
