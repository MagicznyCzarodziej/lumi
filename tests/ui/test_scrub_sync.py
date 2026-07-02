"""Scrub position sync tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from lumi.ui.player.controller.events import PlaybackState
from lumi.ui.player.overlay.input_router import Command, RoutedCommand
from lumi.ui.player.overlay.overlay import PlayerOverlay
from lumi.ui.player.overlay.state import OverlayState, View


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _controller_with_stale_cache(*, time_pos: float, duration: float) -> MagicMock:
    controller = MagicMock()
    controller.state = PlaybackState(
        has_media=True,
        paused=False,
        time_pos=0.0,
        duration=0.0,
        volume=100.0,
        muted=False,
        sid=None,
        aid=None,
    )
    controller.time_pos.return_value = time_pos
    controller.duration.return_value = duration
    controller.has_media.return_value = True
    controller.is_paused.return_value = False
    return controller


def test_key_scrub_reads_live_playback_position(qapp) -> None:
    controller = _controller_with_stale_cache(time_pos=45.0, duration=120.0)
    overlay = PlayerOverlay(controller)
    overlay._rt.state = OverlayState(view=View.WATCHING)

    overlay.execute_command(RoutedCommand(Command.START_KEY_SCRUB, delta=1))

    assert overlay.state.duration == 120.0
    assert overlay.state.time_pos == 55.0
    controller.seek_relative.assert_called_once_with(10.0)
    controller.seek_fraction.assert_not_called()


def test_key_scrub_without_duration_uses_relative_seek(qapp) -> None:
    controller = _controller_with_stale_cache(time_pos=12.0, duration=0.0)
    overlay = PlayerOverlay(controller)
    overlay._rt.state = OverlayState(view=View.WATCHING)

    overlay.execute_command(RoutedCommand(Command.START_KEY_SCRUB, delta=1))

    controller.seek_relative.assert_called_once_with(10.0)
    controller.seek_fraction.assert_not_called()
    scrub = overlay.state.scrub
    assert scrub is None or not scrub.keyboard_scrubbing


def test_quick_key_scrub_release_does_not_seek_to_start(qapp) -> None:
    controller = _controller_with_stale_cache(time_pos=45.0, duration=120.0)
    overlay = PlayerOverlay(controller)
    overlay._rt.state = OverlayState(view=View.WATCHING)

    overlay.execute_command(RoutedCommand(Command.START_KEY_SCRUB, delta=1))
    overlay.execute_command(RoutedCommand(Command.STOP_KEY_SCRUB))

    controller.seek_fraction.assert_not_called()
    assert controller.seek_relative.call_count == 1


def test_key_scrub_release_keeps_scrubber_visible(qapp) -> None:
    controller = _controller_with_stale_cache(time_pos=45.0, duration=120.0)
    overlay = PlayerOverlay(controller)
    overlay._rt.state = OverlayState(view=View.WATCHING)

    overlay.execute_command(RoutedCommand(Command.START_KEY_SCRUB, delta=1))
    assert overlay.state.view == View.SCRUB

    overlay.execute_command(RoutedCommand(Command.STOP_KEY_SCRUB))

    assert overlay.state.view == View.SCRUB
    assert overlay._rt.hide_timer.isActive()
    assert overlay._rt.hide_timer.remainingTime() <= overlay.SCRUB_HIDE_MS


def test_key_scrub_updates_overlay_duration_for_timeline(qapp) -> None:
    controller = _controller_with_stale_cache(time_pos=10.0, duration=90.0)
    overlay = PlayerOverlay(controller)
    overlay._rt.state = OverlayState(view=View.WATCHING, duration=0.0, time_pos=0.0)

    overlay.execute_command(RoutedCommand(Command.START_KEY_SCRUB, delta=1))

    assert overlay.state.duration == 90.0
    assert overlay.state.time_pos == 20.0
