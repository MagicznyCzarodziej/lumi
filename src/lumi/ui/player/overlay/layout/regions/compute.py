"""Layout orchestration — dispatch by overlay view."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import QRect

from lumi.domain.subtitles.browse import BrowseRow
from lumi.ui.player.overlay.layout.metrics import compute_ui_metrics
from lumi.ui.player.overlay.layout.regions.browse import layout_browse_panel
from lumi.ui.player.overlay.layout.regions.controls import layout_controls_geometry
from lumi.ui.player.overlay.layout.regions.tracks import layout_track_panel
from lumi.ui.player.overlay.layout.regions.types import LayoutSnapshot
from lumi.ui.player.overlay.layout.regions.video import layout_video_panel
from lumi.ui.player.overlay.state import TrackKind, TrackRow, View


def compute_layout(
    w: int,
    h: int,
    view: View,
    track_kind: TrackKind,
    track_rows: list[TrackRow],
    *,
    browse_path: PurePosixPath | None = None,
    browse_rows: list[BrowseRow] | None = None,
    panel_scroll_y: int = 0,
    prev_ep: bool = False,
    next_ep: bool = False,
) -> LayoutSnapshot:
    """Build a layout snapshot for the current overlay view and widget size.

    Called on every resize and whenever scroll position or row data changes.
    ``panel_scroll_y`` is the persisted scroll offset from overlay state.
    """
    metrics = compute_ui_metrics(w, h)
    hit_regions: dict[str, QRect] = {}
    seek_inner = QRect()
    elapsed_rect = QRect()
    total_rect = QRect()
    time_font_size = metrics.font_sm
    panel_w = metrics.panel_w_min
    track_footer_top: int | None = None
    panel_scroll_max = 0
    panel_list_top = 0
    panel_list_bottom = h
    panel_row_tops: dict[str, int] = {}
    scroll_y = panel_scroll_y

    if view in (View.CONTROLS, View.SCRUB):
        cross, hints, seek_inner, elapsed_rect, total_rect, time_font_size = (
            layout_controls_geometry(
                w,
                h,
                metrics,
                prev_ep=prev_ep and view == View.CONTROLS,
                next_ep=next_ep and view == View.CONTROLS,
            )
        )
        if view == View.CONTROLS:
            # SCRUB view shows only the timeline — no cross or corner hints.
            hit_regions.update(cross)
            hit_regions.update(hints)
        # Taller hit target above the thin bottom bar for easier scrubbing.
        hit_regions["seek"] = seek_inner.adjusted(
            0,
            -(elapsed_rect.height() + max(8, metrics.gap)),
            0,
            0,
        )
    elif view == View.TRACKS:
        tracks = layout_track_panel(
            w=w,
            h=h,
            m=metrics,
            track_kind=track_kind,
            track_rows=track_rows,
            panel_scroll_y=panel_scroll_y,
        )
        panel_w = tracks.panel_w
        hit_regions = tracks.hit_regions
        panel_row_tops = tracks.panel_row_tops
        scroll_y = tracks.panel_scroll_y
        panel_scroll_max = tracks.panel_scroll_max
        panel_list_top = tracks.panel_list_top
        panel_list_bottom = tracks.panel_list_bottom
        track_footer_top = tracks.track_footer_top
    elif view == View.VIDEO:
        panel_w, scroll = layout_video_panel(
            w=w,
            h=h,
            m=metrics,
            panel_scroll_y=panel_scroll_y,
        )
        hit_regions = scroll.hit_regions
        panel_row_tops = scroll.panel_row_tops
        scroll_y = scroll.panel_scroll_y
        panel_scroll_max = scroll.panel_scroll_max
        panel_list_top = scroll.panel_list_top
        panel_list_bottom = scroll.panel_list_bottom
    elif view == View.SUBTITLE_BROWSE:
        panel_w, scroll = layout_browse_panel(
            w=w,
            h=h,
            m=metrics,
            browse_path=browse_path,
            browse_rows=browse_rows or [],
            panel_scroll_y=panel_scroll_y,
        )
        hit_regions = scroll.hit_regions
        panel_row_tops = scroll.panel_row_tops
        scroll_y = scroll.panel_scroll_y
        panel_scroll_max = scroll.panel_scroll_max
        panel_list_top = scroll.panel_list_top
        panel_list_bottom = scroll.panel_list_bottom

    return LayoutSnapshot(
        hit_regions=hit_regions,
        seek_inner=seek_inner,
        elapsed_rect=elapsed_rect,
        total_rect=total_rect,
        panel_w=panel_w,
        time_font_size=time_font_size,
        metrics=metrics,
        track_footer_top=track_footer_top,
        panel_scroll_y=scroll_y,
        panel_scroll_max=panel_scroll_max,
        panel_list_top=panel_list_top,
        panel_list_bottom=panel_list_bottom,
        panel_row_tops=panel_row_tops,
    )
