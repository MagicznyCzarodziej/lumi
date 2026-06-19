"""libmpv dylib discovery (macOS)."""

from __future__ import annotations

import ctypes.util
import os
from pathlib import Path


def prepare_libmpv() -> None:
    if ctypes.util.find_library("mpv") is not None:
        return

    for lib in (
        Path("/opt/homebrew/lib/libmpv.dylib"),
        Path("/usr/local/lib/libmpv.dylib"),
    ):
        if not lib.exists():
            continue
        lib_path = str(lib)
        original = ctypes.util.find_library
        ctypes.util.find_library = lambda name, _path=lib_path, _orig=original: (  # type: ignore[method-assign, misc]
            _path if name == "mpv" else _orig(name)
        )
        lib_dir = str(lib.parent)
        fallback = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            f"{lib_dir}{os.pathsep}{fallback}" if fallback else lib_dir
        )
        return
