"""Player input router tests."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from lumi.ui.player.overlay.input_router import Command, InputRouter
from lumi.ui.player.overlay.state import OverlayState, TrackRow, View, move_track_action_focus


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _key(key: Qt.Key, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QKeyEvent.Type.KeyPress, key, modifiers)


def _key_release(key: Qt.Key, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QKeyEvent.Type.KeyRelease, key, modifiers)

def test_m_toggles_mute(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)

    routed = router.route_key(_key(Qt.Key.Key_M), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.TOGGLE_MUTE

    no_media = router.route_key(_key(Qt.Key.Key_M), state, has_media=False)
    assert no_media is None


def test_plus_and_minus_start_volume_adjust(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)

    up = router.route_key(_key(Qt.Key.Key_Equal, Qt.KeyboardModifier.ShiftModifier), state, has_media=True)
    assert up is not None
    assert up.command == Command.START_VOLUME_ADJUST
    assert up.delta == 1
    assert up.volume_step == 1

    down = router.route_key(_key(Qt.Key.Key_Minus), state, has_media=True)
    assert down is not None
    assert down.command == Command.START_VOLUME_ADJUST
    assert down.delta == -1
    assert down.volume_step == 1

    ctrl_up = router.route_key(
        _key(Qt.Key.Key_Equal, Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier),
        state,
        has_media=True,
    )
    assert ctrl_up is not None
    assert ctrl_up.volume_step == 5

    stop = router.route_key_release(_key_release(Qt.Key.Key_Minus), state)
    assert stop is not None
    assert stop.command == Command.STOP_VOLUME_ADJUST


def test_watching_left_starts_scrub(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)
    routed = router.route_key(_key(Qt.Key.Key_Left), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.START_KEY_SCRUB
    assert routed.delta == -1


def test_watching_right_starts_scrub(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)
    routed = router.route_key(_key(Qt.Key.Key_Right), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.START_KEY_SCRUB
    assert routed.delta == 1


def test_watching_space_shows_controls(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)
    routed = router.route_key(_key(Qt.Key.Key_Space), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.TOGGLE_PAUSE


def test_watching_backspace_hides_ui(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)
    routed = router.route_key(_key(Qt.Key.Key_Backspace), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.HIDE_UI


def test_watching_grave_accent_hides_ui(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)
    routed = router.route_key(_key(Qt.Key.Key_QuoteLeft), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.HIDE_UI


def test_ctrl_zero_seeks_to_start(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.WATCHING)

    routed = router.route_key(
        _key(Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier),
        state,
        has_media=True,
    )
    assert routed is not None
    assert routed.command == Command.SEEK_TO_FRACTION
    assert routed.fraction == 0.0

    assert router.route_key(_key(Qt.Key.Key_0), state, has_media=True).command == Command.SHOW_CONTROLS
    assert (
        router.route_key(
            _key(Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier),
            state,
            has_media=False,
        )
        is None
    )


def test_scrub_left_continues_scrub(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.SCRUB)
    routed = router.route_key(_key(Qt.Key.Key_Left), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.START_KEY_SCRUB
    assert routed.delta == -1


def test_scrub_up_shows_controls(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.SCRUB)
    routed = router.route_key(_key(Qt.Key.Key_Up), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.TIMELINE_UP


def test_scrub_down_dismisses(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.SCRUB)
    routed = router.route_key(_key(Qt.Key.Key_Down), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.TIMELINE_DOWN


def test_tracks_right_moves_to_save_action(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=1,
        track_rows=[
            TrackRow(label="Off", mpv_id=0),
            TrackRow(label="NapiProjekt (ENG)", mpv_id=1, show_napi_save=True, show_napi_delete=True),
        ],
    )
    routed = router.route_key(_key(Qt.Key.Key_Right), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.MOVE_TRACK_ACTION_FOCUS
    assert routed.delta == 1


def test_tracks_right_on_save_moves_to_delete(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=0,
        track_action_focus="save",
        track_rows=[
            TrackRow(label="NapiProjekt (ENG)", mpv_id=1, show_napi_save=True, show_napi_delete=True),
        ],
    )
    routed = router.route_key(_key(Qt.Key.Key_Right), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.MOVE_TRACK_ACTION_FOCUS
    assert routed.delta == 1


def test_tracks_left_from_save_returns_to_row(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=0,
        track_action_focus="save",
        track_rows=[
            TrackRow(label="NapiProjekt (ENG)", mpv_id=1, show_napi_save=True, show_napi_delete=True),
        ],
    )
    next_state = move_track_action_focus(state, -1)
    assert next_state.track_action_focus is None


def test_tracks_enter_on_action_activates(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=0,
        track_action_focus="delete",
        track_rows=[
            TrackRow(label="NapiProjekt (ENG)", mpv_id=1, show_napi_save=True, show_napi_delete=True),
        ],
    )
    routed = router.route_key(_key(Qt.Key.Key_Return), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.ACTIVATE_TRACK_ACTION


def test_tracks_left_on_delay_row_adjusts(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=1,
        track_rows=[
            TrackRow(label="English", mpv_id=1),
            TrackRow(label="Delay", is_action=True, is_sub_delay_control=True),
        ],
    )
    routed = router.route_key(_key(Qt.Key.Key_Left), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.ADJUST_SUB_DELAY
    assert routed.delta == -1


def test_tracks_right_on_delay_row_adjusts(qapp) -> None:
    router = InputRouter()
    state = OverlayState(
        view=View.TRACKS,
        track_focus=1,
        track_rows=[
            TrackRow(label="English", mpv_id=1),
            TrackRow(label="Delay", is_action=True, is_sub_delay_control=True),
        ],
    )
    routed = router.route_key(_key(Qt.Key.Key_Right), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.ADJUST_SUB_DELAY
    assert routed.delta == 1


def test_v_opens_video_drawer(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.CONTROLS)
    routed = router.route_key(_key(Qt.Key.Key_V), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.OPEN_VIDEO


def test_v_closes_video_drawer(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.VIDEO)
    routed = router.route_key(_key(Qt.Key.Key_V), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.CLOSE_VIDEO


def test_video_drawer_selects_aspect(qapp) -> None:
    router = InputRouter()
    state = OverlayState(view=View.VIDEO, video_focus=2)
    routed = router.route_key(_key(Qt.Key.Key_Return), state, has_media=True)
    assert routed is not None
    assert routed.command == Command.SELECT_VIDEO_ASPECT
    assert routed.video_aspect_index == 2
