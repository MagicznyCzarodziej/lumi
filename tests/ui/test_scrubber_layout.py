"""Scrubber / timeline layout tests."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from lumi.ui.player.overlay.layout.regions import compute_layout
from lumi.ui.player.overlay.state import TrackKind, View


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_scrubber_is_full_bleed_and_bottom_flushed(qapp) -> None:
    w, h = 1280, 720
    layout = compute_layout(w, h, View.SCRUB, TrackKind.SUBTITLES, [])

    seek = layout.seek_inner
    assert seek.left() == 0
    assert seek.right() == w - 1
    assert seek.bottom() == h - 1
    assert seek.top() == h - seek.height()


def test_scrubber_time_labels_sit_above_bar(qapp) -> None:
    w, h = 1280, 720
    layout = compute_layout(w, h, View.SCRUB, TrackKind.SUBTITLES, [])

    assert layout.elapsed_rect.bottom() < layout.seek_inner.top()
    assert layout.total_rect.bottom() < layout.seek_inner.top()


def test_scrubber_time_labels_hug_side_edges(qapp) -> None:
    w, h = 1280, 720
    layout = compute_layout(w, h, View.SCRUB, TrackKind.SUBTITLES, [])

    assert layout.elapsed_rect.left() <= max(6, int(w * 0.006)) + 2
    assert layout.total_rect.right() >= w - max(6, int(w * 0.006)) - 2


def test_controls_centered_above_scrubber(qapp) -> None:
    w, h = 1280, 720
    layout = compute_layout(w, h, View.CONTROLS, TrackKind.SUBTITLES, [])

    center = layout.hit_regions["center"]
    assert abs(center.center().x() - w // 2) <= 4
    assert center.bottom() < layout.elapsed_rect.top()
    assert layout.elapsed_rect.bottom() < layout.seek_inner.top()


def test_corner_hints_vertically_centered(qapp) -> None:
    w, h = 1280, 720
    layout = compute_layout(w, h, View.CONTROLS, TrackKind.SUBTITLES, [])

    video = layout.hit_regions["video"]
    audio = layout.hit_regions["audio"]
    stack_mid = (video.top() + audio.bottom()) // 2
    assert abs(stack_mid - h // 2) <= 24
