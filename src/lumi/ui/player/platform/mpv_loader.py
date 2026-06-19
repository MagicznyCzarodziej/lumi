"""Lazy libmpv import — prepare_libmpv must run before first use."""

from __future__ import annotations

import ctypes.util
from types import ModuleType

from lumi.ui.player.platform.libmpv import prepare_libmpv

_mpv: ModuleType | None = None


def get_mpv() -> ModuleType:
    global _mpv
    if _mpv is not None:
        return _mpv

    prepare_libmpv()
    if ctypes.util.find_library("mpv") is None:
        msg = (
            "Cannot find libmpv. Install mpv (e.g. brew install mpv on macOS) "
            "and ensure libmpv.dylib is on the library search path."
        )
        raise OSError(msg)

    import mpv as mpv_module

    _mpv = mpv_module
    return _mpv
