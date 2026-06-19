"""Global UI scale for library chrome (excludes video player overlay)."""

from __future__ import annotations

UI_SCALE = 1.5


def scaled(value: int | float) -> int:
    return max(1, round(float(value) * UI_SCALE))
