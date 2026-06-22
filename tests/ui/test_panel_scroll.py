"""Tests for drawer panel scroll math."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from lumi.ui.player.overlay.layout.panel_scroll import clamp_panel_scroll, scroll_to_show_item
from lumi.ui.player.overlay.layout.regions import compute_layout
from lumi.ui.player.overlay.state import TrackKind, TrackRow, View


def test_clamp_panel_scroll() -> None:
    assert clamp_panel_scroll(5, 10) == 5
    assert clamp_panel_scroll(-3, 10) == 0
    assert clamp_panel_scroll(99, 10) == 10
    assert clamp_panel_scroll(5, 0) == 0


def test_scroll_to_show_item_moves_down_when_below_viewport() -> None:
    scroll = scroll_to_show_item(
        500,
        40,
        viewport_top=100,
        viewport_bottom=300,
        scroll_y=0,
    )
    assert scroll == 240


def test_scroll_to_show_item_moves_up_when_above_viewport() -> None:
    scroll = scroll_to_show_item(
        120,
        40,
        viewport_top=100,
        viewport_bottom=300,
        scroll_y=200,
    )
    assert scroll == 20


def test_track_panel_scroll_max_with_long_list_and_footer() -> None:
    QApplication.instance() or QApplication([])
    entries = [TrackRow(label=f"Subtitle track {i}") for i in range(40)]
    footer = [
        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True),
        TrackRow(label="Browse…", opens_browse=True, is_action=True),
    ]
    layout = compute_layout(
        400,
        800,
        View.TRACKS,
        TrackKind.SUBTITLES,
        entries + footer,
    )
    assert layout.panel_scroll_max > 0
    assert layout.panel_list_bottom < 800
    assert layout.track_footer_top is not None
    assert layout.track_footer_top < 800


def test_track_footer_bottom_margin_matches_sides() -> None:
    QApplication.instance() or QApplication([])
    h = 800
    footer = [
        TrackRow(label="Download from NapiProjekt", opens_napi_download=True, is_action=True),
        TrackRow(label="Browse…", opens_browse=True, is_action=True),
    ]
    layout = compute_layout(
        400,
        h,
        View.TRACKS,
        TrackKind.SUBTITLES,
        [TrackRow(label="English")] + footer,
    )
    browse_rect = layout.hit_regions["track:2"]
    side_pad = layout.metrics.track_pad_x
    assert h - (browse_rect.y() + browse_rect.height()) == side_pad
