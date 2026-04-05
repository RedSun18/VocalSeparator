"""
fix_dylib.py — PyInstaller runtime hook for torchaudio / torch dylib resolution.

The problem:
  torchaudio._extension loads libtorchaudio.so via ctypes at import time.
  Inside a .app bundle, PyInstaller places all binaries under:
    Contents/Frameworks/
  but torchaudio's __file__ is at:
    Contents/Frameworks/torchaudio/__init__.pyc
  and it looks for libtorchaudio.so relative to its own location.
  The dylinker never searches ../  so it fails with "dylib not found".

The fix:
  At runtime, before any torchaudio import happens, add the Frameworks
  directory (one level up from the torchaudio package) to DYLD_LIBRARY_PATH
  so the macOS dynamic linker finds libtorchaudio.so and friends.

  We also patch torchaudio._extension._load_lib() to use an absolute path
  as a belt-and-suspenders measure.
"""

import os
import sys

if getattr(sys, "frozen", False):
    # _MEIPASS is the Contents/Frameworks/ directory
    frameworks = sys._MEIPASS

    # Tell the macOS dynamic linker to search here
    existing = os.environ.get("DYLD_LIBRARY_PATH", "")
    os.environ["DYLD_LIBRARY_PATH"] = (
        frameworks + (":" + existing if existing else "")
    )
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = frameworks

    # Also add to LD_LIBRARY_PATH for any ctypes.cdll.LoadLibrary calls
    existing_ld = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = (
        frameworks + (":" + existing_ld if existing_ld else "")
    )

    # Pre-load libtorchaudio with an explicit absolute path so that when
    # torchaudio._extension calls ctypes.cdll.LoadLibrary("libtorchaudio.so")
    # the dylinker finds the already-loaded handle instead of searching.
    import ctypes
    import glob

    for pattern in ["libtorchaudio*.so", "libtorchaudio*.dylib"]:
        for lib in glob.glob(os.path.join(frameworks, pattern)):
            try:
                ctypes.CDLL(lib)
                print(f"[fix_dylib] pre-loaded: {os.path.basename(lib)}")
            except OSError as e:
                print(f"[fix_dylib] warning: could not pre-load {lib}: {e}")
