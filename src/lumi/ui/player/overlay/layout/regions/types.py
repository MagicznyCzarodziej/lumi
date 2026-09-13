"""Layout output types — geometry snapshot consumed by paint and input routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QRect

from lumi.ui.player.overlay.layout.metrics import UiMetrics


class HitRegion(str, Enum):
    """Stable keys for transport controls and corner hints (mouse routing)."""

    OPEN = "open"
    M1 = "m1"
    CENTER = "center"
    P1 = "p1"
    SUBS = "subs"
    AUDIO = "audio"
    VIDEO = "video"
    SEEK = "seek"


@dataclass
class LayoutSnapshot:
    """Immutable layout pass for one overlay size + view.

    ``hit_regions`` maps string keys to screen-space ``QRect``s used by
    ``InputRouter`` and paint delegates. Row keys follow ``track:{i}``,
    ``video:{i}``, ``browse:{i}``; action suffixes use ``:save``, ``:delete``,
    ``:delay-earlier``, ``:delay-later``.

    Scrollable panels expose content-space tops in ``panel_row_tops`` (unscrolled)
    and clip between ``panel_list_top`` / ``panel_list_bottom``.
    """

    hit_regions: dict[str, QRect]
    seek_inner: QRect
    elapsed_rect: QRect
    total_rect: QRect
    panel_w: int
    time_font_size: int
    metrics: UiMetrics
    track_footer_top: int | None = None
    panel_scroll_y: int = 0
    panel_scroll_max: int = 0
    panel_list_top: int = 0
    panel_list_bottom: int = 0
    panel_row_tops: dict[str, int] = field(default_factory=dict)
