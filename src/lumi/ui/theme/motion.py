"""Shared motion tokens and easing helpers."""

from PySide6.QtGui import QColor

FOCUS_POP_FRAME_INTERVAL_MS = 16
FOCUS_POP_DURATION_MS = 450
FOCUS_POP_START_SCALE = 0.96
FOCUS_POP_START_SCALE_COMPACT = 0.86
FOCUS_POP_GLOW_LIGHTENING = 45
FOCUS_POP_GLOW_LIGHTENING_COMPACT = 70


def focus_pop_scale(progress: float, *, start_scale: float = FOCUS_POP_START_SCALE) -> float:
    clamped = max(0.0, min(progress, 1.0))
    eased = 1.0 - (1.0 - clamped) ** 3
    return start_scale + (1.0 - start_scale) * eased


def focus_pop_scale_compact(progress: float) -> float:
    return focus_pop_scale(progress, start_scale=FOCUS_POP_START_SCALE_COMPACT)


def focus_pop_glow(progress: float) -> float:
    clamped = max(0.0, min(progress, 1.0))
    return 4.0 * clamped * (1.0 - clamped)


def focus_pop_highlight_color(
    base: QColor,
    progress: float | None,
    *,
    glow_lightening: int = FOCUS_POP_GLOW_LIGHTENING,
) -> QColor:
    if progress is None:
        return base
    return base.lighter(
        100 + round(glow_lightening * focus_pop_glow(progress))
    )
