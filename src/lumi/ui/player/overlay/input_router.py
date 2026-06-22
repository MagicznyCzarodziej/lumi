"""Keyboard and mouse input routing (no mpv dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QKeyEvent, QMouseEvent

from lumi.ui.components.keyboard_helpers import is_back_key
from lumi.ui.player.overlay.state import (
    CROSS_ORDER,
    FocusZone,
    OverlayState,
    TrackKind,
    View,
    track_row_actions,
)


def is_dismiss_key(key: int) -> bool:
    return is_back_key(key)


class Command(Enum):
    OPEN_VIDEO = auto()
    CLOSE_VIDEO = auto()
    MOVE_VIDEO_FOCUS = auto()
    SELECT_VIDEO_ASPECT = auto()
    OPEN_FILE = auto()
    TOGGLE_PAUSE = auto()
    SHOW_CONTROLS = auto()
    DISMISS_CONTROLS = auto()
    HIDE_UI = auto()
    OPEN_TRACKS = auto()
    CLOSE_TRACKS = auto()
    OPEN_SUBTITLE_BROWSE = auto()
    CLOSE_SUBTITLE_BROWSE = auto()
    BROWSE_BACK = auto()
    ACTIVATE_BROWSE = auto()
    MOVE_BROWSE_FOCUS = auto()
    MOVE_CROSS_FOCUS = auto()
    TOGGLE_FOCUS_ZONE = auto()
    ACTIVATE_CROSS = auto()
    SELECT_TRACK = auto()
    MOVE_TRACK_FOCUS = auto()
    MOVE_TRACK_ACTION_FOCUS = auto()
    ACTIVATE_TRACK_ACTION = auto()
    ADJUST_SUB_DELAY = auto()
    START_MOUSE_SCRUB = auto()
    MOUSE_SCRUB = auto()
    FINISH_MOUSE_SCRUB = auto()
    START_KEY_SCRUB = auto()
    STOP_KEY_SCRUB = auto()
    TIMELINE_UP = auto()
    TIMELINE_DOWN = auto()
    HIT = auto()
    KEYBOARD_ACTIVITY = auto()
    CLICK_OUTSIDE = auto()
    START_VOLUME_ADJUST = auto()
    STOP_VOLUME_ADJUST = auto()
    TOGGLE_MUTE = auto()
    SEEK_TO_FRACTION = auto()


_VOLUME_RELEASE_KEYS = frozenset({Qt.Key.Key_Plus, Qt.Key.Key_Minus, Qt.Key.Key_Equal})


def _volume_key_delta(key: int, modifiers: Qt.KeyboardModifier) -> int | None:
    if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) and (
        key == Qt.Key.Key_Plus or modifiers & Qt.KeyboardModifier.ShiftModifier
    ):
        return 1
    if key == Qt.Key.Key_Minus:
        return -1
    return None


def _volume_step_base(modifiers: Qt.KeyboardModifier) -> int:
    return 5 if modifiers & Qt.KeyboardModifier.ControlModifier else 1


@dataclass(frozen=True)
class RoutedCommand:
    command: Command
    delta: int = 0
    fraction: float = 0.0
    track_kind: TrackKind | None = None
    track_index: int = 0
    browse_index: int = 0
    hit_key: str = ""
    pos: QPoint | None = None
    volume_step: int = 1
    video_aspect_index: int = 0


class InputRouter:
    def route_key(
        self,
        event: QKeyEvent,
        state: OverlayState,
        *,
        has_media: bool,
    ) -> RoutedCommand | None:
        key = event.key()

        if key == Qt.Key.Key_O:
            return RoutedCommand(Command.OPEN_FILE)

        if key == Qt.Key.Key_Space:
            return RoutedCommand(Command.TOGGLE_PAUSE)

        if key == Qt.Key.Key_S:
            if state.view == View.SUBTITLE_BROWSE:
                return RoutedCommand(Command.CLOSE_SUBTITLE_BROWSE)
            if state.view == View.TRACKS and state.track_kind == TrackKind.SUBTITLES:
                return RoutedCommand(Command.CLOSE_TRACKS)
            return RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.SUBTITLES)

        if key == Qt.Key.Key_A:
            if state.view == View.TRACKS and state.track_kind == TrackKind.AUDIO:
                return RoutedCommand(Command.CLOSE_TRACKS)
            return RoutedCommand(Command.OPEN_TRACKS, track_kind=TrackKind.AUDIO)

        if key == Qt.Key.Key_V:
            if state.view == View.VIDEO:
                return RoutedCommand(Command.CLOSE_VIDEO)
            return RoutedCommand(Command.OPEN_VIDEO)

        if has_media:
            if (
                key == Qt.Key.Key_0
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                if event.isAutoRepeat():
                    return None
                return RoutedCommand(Command.SEEK_TO_FRACTION, fraction=0.0)

            if key == Qt.Key.Key_M:
                return RoutedCommand(Command.TOGGLE_MUTE)

            volume_direction = _volume_key_delta(key, event.modifiers())
            if volume_direction is not None:
                if event.isAutoRepeat():
                    return None
                return RoutedCommand(
                    Command.START_VOLUME_ADJUST,
                    delta=volume_direction,
                    volume_step=_volume_step_base(event.modifiers()),
                )

        if has_media and state.view == View.WATCHING:
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                if event.isAutoRepeat():
                    return None
                delta = -1 if key == Qt.Key.Key_Left else 1
                return RoutedCommand(Command.START_KEY_SCRUB, delta=delta)
            if not is_dismiss_key(key):
                return RoutedCommand(Command.SHOW_CONTROLS)

        if state.view == View.SUBTITLE_BROWSE:
            if is_dismiss_key(key):
                return RoutedCommand(Command.BROWSE_BACK)
            if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
                return RoutedCommand(Command.MOVE_BROWSE_FOCUS, delta=-1)
            if key == Qt.Key.Key_Down:
                return RoutedCommand(Command.MOVE_BROWSE_FOCUS, delta=1)
            if key == Qt.Key.Key_Left:
                return RoutedCommand(Command.BROWSE_BACK)
            if key in (Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                return RoutedCommand(Command.ACTIVATE_BROWSE, browse_index=state.browse_focus)
            return None

        if is_dismiss_key(key):
            return RoutedCommand(Command.HIDE_UI)

        if state.view == View.VIDEO:
            if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
                return RoutedCommand(Command.MOVE_VIDEO_FOCUS, delta=-1)
            if key == Qt.Key.Key_Down:
                return RoutedCommand(Command.MOVE_VIDEO_FOCUS, delta=1)
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                return RoutedCommand(
                    Command.SELECT_VIDEO_ASPECT,
                    video_aspect_index=state.video_focus,
                )
            return None

        if state.view == View.TRACKS:
            rows = state.track_rows or []
            row = rows[state.track_focus] if 0 <= state.track_focus < len(rows) else None
            actions = track_row_actions(row) if row is not None else ()

            if row is not None and row.is_sub_delay_control and state.track_action_focus is None:
                if key == Qt.Key.Key_Left:
                    return RoutedCommand(Command.ADJUST_SUB_DELAY, delta=-1)
                if key == Qt.Key.Key_Right:
                    return RoutedCommand(Command.ADJUST_SUB_DELAY, delta=1)

            if key == Qt.Key.Key_Right:
                if not actions:
                    return None
                if state.track_action_focus is None:
                    return RoutedCommand(Command.MOVE_TRACK_ACTION_FOCUS, delta=1)
                try:
                    idx = actions.index(state.track_action_focus)
                except ValueError:
                    return RoutedCommand(Command.MOVE_TRACK_ACTION_FOCUS, delta=1)
                if idx < len(actions) - 1:
                    return RoutedCommand(Command.MOVE_TRACK_ACTION_FOCUS, delta=1)
                return None

            if key == Qt.Key.Key_Left:
                if state.track_action_focus is None:
                    return None
                return RoutedCommand(Command.MOVE_TRACK_ACTION_FOCUS, delta=-1)

            if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
                return RoutedCommand(Command.MOVE_TRACK_FOCUS, delta=-1)
            if key == Qt.Key.Key_Down:
                return RoutedCommand(Command.MOVE_TRACK_FOCUS, delta=1)
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if state.track_action_focus is not None:
                    return RoutedCommand(Command.ACTIVATE_TRACK_ACTION)
                return RoutedCommand(Command.SELECT_TRACK, track_index=state.track_focus)
            return None

        if state.view == View.SCRUB:
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                if event.isAutoRepeat():
                    return None
                delta = -1 if key == Qt.Key.Key_Left else 1
                return RoutedCommand(Command.START_KEY_SCRUB, delta=delta)
            if key == Qt.Key.Key_Space:
                return RoutedCommand(Command.TOGGLE_PAUSE)
            if is_dismiss_key(key):
                return RoutedCommand(Command.HIDE_UI)
            return RoutedCommand(Command.KEYBOARD_ACTIVITY)

        if state.view != View.CONTROLS:
            return None

        if key == Qt.Key.Key_Tab:
            return RoutedCommand(Command.TOGGLE_FOCUS_ZONE)

        if key == Qt.Key.Key_Up:
            if state.focus_zone == FocusZone.TIMELINE:
                return RoutedCommand(Command.TIMELINE_UP)
            if state.focus_zone == FocusZone.CONTROLS:
                return RoutedCommand(Command.DISMISS_CONTROLS)
            return RoutedCommand(Command.KEYBOARD_ACTIVITY)

        if key == Qt.Key.Key_Down:
            if state.focus_zone == FocusZone.TIMELINE:
                return RoutedCommand(Command.TIMELINE_DOWN)
            if state.focus_zone == FocusZone.CONTROLS:
                return RoutedCommand(Command.TOGGLE_FOCUS_ZONE)
            return RoutedCommand(Command.KEYBOARD_ACTIVITY)

        if key == Qt.Key.Key_Left:
            if state.focus_zone == FocusZone.TIMELINE:
                if event.isAutoRepeat():
                    return None
                return RoutedCommand(Command.START_KEY_SCRUB, delta=-1)
            return RoutedCommand(Command.MOVE_CROSS_FOCUS, delta=-1)

        if key == Qt.Key.Key_Right:
            if state.focus_zone == FocusZone.TIMELINE:
                if event.isAutoRepeat():
                    return None
                return RoutedCommand(Command.START_KEY_SCRUB, delta=1)
            return RoutedCommand(Command.MOVE_CROSS_FOCUS, delta=1)

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if state.focus_zone == FocusZone.CONTROLS:
                return RoutedCommand(Command.ACTIVATE_CROSS)
            return RoutedCommand(Command.KEYBOARD_ACTIVITY)

        return None

    def route_key_release(
        self,
        event: QKeyEvent,
        state: OverlayState,
    ) -> RoutedCommand | None:
        if event.key() in _VOLUME_RELEASE_KEYS and not event.isAutoRepeat():
            return RoutedCommand(Command.STOP_VOLUME_ADJUST)
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right) and not event.isAutoRepeat():
            scrub = state.scrub
            if scrub is not None and scrub.keyboard_scrubbing:
                return RoutedCommand(Command.STOP_KEY_SCRUB)
        return None

    def route_mouse_press(
        self,
        event: QMouseEvent,
        state: OverlayState,
        hit_regions: dict[str, QRect],
        *,
        has_media: bool,
        in_controls_area: Callable[[QPoint], bool],
    ) -> RoutedCommand | None:
        if event.button() != Qt.MouseButton.LeftButton:
            return None

        if not has_media:
            return RoutedCommand(Command.OPEN_FILE)

        if state.view == View.WATCHING:
            return RoutedCommand(Command.SHOW_CONTROLS)

        pos = event.position().toPoint()

        if state.view == View.TRACKS:
            for key, rect in hit_regions.items():
                if (
                    key.startswith("track:")
                    and (
                        ":save" in key
                        or ":delete" in key
                        or ":delay-earlier" in key
                        or ":delay-later" in key
                    )
                    and rect.contains(pos)
                ):
                    return RoutedCommand(Command.HIT, hit_key=key)
            for key, rect in hit_regions.items():
                if key.startswith("track:") and rect.contains(pos):
                    return RoutedCommand(Command.HIT, hit_key=key)
            return RoutedCommand(Command.CLOSE_TRACKS)

        if state.view == View.VIDEO:
            for key, rect in hit_regions.items():
                if key.startswith("video:") and rect.contains(pos):
                    return RoutedCommand(Command.HIT, hit_key=key)
            return RoutedCommand(Command.CLOSE_VIDEO)

        if state.view == View.SUBTITLE_BROWSE:
            for key, rect in hit_regions.items():
                if key.startswith("browse:") and rect.contains(pos):
                    return RoutedCommand(Command.HIT, hit_key=key)
            return RoutedCommand(Command.CLOSE_SUBTITLE_BROWSE)

        seek = hit_regions.get("seek")
        if seek is not None and seek.contains(pos) and state.view in (View.CONTROLS, View.SCRUB):
            return RoutedCommand(Command.START_MOUSE_SCRUB, pos=pos)

        for key in ("m1", "m10", "center", "p10", "p1", "video", "subs", "audio"):
            region = hit_regions.get(key)
            if region is not None and region.contains(pos):
                return RoutedCommand(Command.HIT, hit_key=key)

        if state.view == View.SCRUB:
            return RoutedCommand(Command.CLICK_OUTSIDE)

        if state.view == View.CONTROLS and not in_controls_area(pos):
            return RoutedCommand(Command.CLICK_OUTSIDE)

        return None

    def route_mouse_move(
        self,
        state: OverlayState,
        *,
        scrubbing: bool,
    ) -> RoutedCommand | None:
        if scrubbing:
            return RoutedCommand(Command.MOUSE_SCRUB)
        if state.view == View.WATCHING:
            return RoutedCommand(Command.SHOW_CONTROLS)
        return None

    def route_mouse_release(
        self,
        event: QMouseEvent,
        *,
        scrubbing: bool,
    ) -> RoutedCommand | None:
        if scrubbing and event.button() == Qt.MouseButton.LeftButton:
            return RoutedCommand(Command.FINISH_MOUSE_SCRUB)
        return None

    @staticmethod
    def cross_hit_keys() -> tuple[str, ...]:
        return CROSS_ORDER
