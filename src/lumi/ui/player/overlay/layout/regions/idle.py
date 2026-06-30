"""Layout for the no-media idle state."""

from __future__ import annotations

from PySide6.QtCore import QRect


def layout_idle_regions(w: int, h: int) -> dict[str, QRect]:
    """Single centered “open” hit target shown before any file is loaded."""
    btn_w, btn_h = 180, 44
    return {"open": QRect((w - btn_w) // 2, h // 2 + 20, btn_w, btn_h)}
