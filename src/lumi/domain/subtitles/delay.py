"""Subtitle sync delay helpers."""

from __future__ import annotations

SUB_DELAY_STEP_SECONDS = 0.1


def format_sub_delay(seconds: float) -> str:
    if abs(seconds) < 0.05:
        return "In sync"
    if seconds > 0:
        return f"{abs(seconds):.1f} s later"
    return f"{abs(seconds):.1f} s earlier"
