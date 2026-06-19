"""Overlay view state and transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from lumi.ui.player.controller.scrub_engine import ScrubState


class View(str, Enum):
    WATCHING = "watching"
    SCRUB = "scrub"
    CONTROLS = "controls"
    TRACKS = "tracks"


class TrackKind(str, Enum):
    SUBTITLES = "subtitles"
    AUDIO = "audio"


class FocusZone(str, Enum):
    CONTROLS = "controls"
    TIMELINE = "timeline"


CROSS_ORDER = ("m1", "m10", "center", "p10", "p1")


@dataclass
class OverlayState:
    view: View = View.WATCHING
    focus_zone: FocusZone = FocusZone.CONTROLS
    cross_focus: str = "center"
    track_kind: TrackKind = TrackKind.SUBTITLES
    track_focus: int = 0
    scrub: ScrubState | None = None
    volume_flash: bool = False
    volume: float = 100.0
    muted: bool = False
    time_pos: float = 0.0
    duration: float = 0.0
    paused: bool = True
    track_rows: list[tuple[int | None, str]] | None = None
    panel_w: int = 340

    def ensure_scrub(self) -> ScrubState:
        if self.scrub is None:
            self.scrub = ScrubState()
        return self.scrub


def move_cross_focus(state: OverlayState, delta: int) -> OverlayState:
    try:
        idx = CROSS_ORDER.index(state.cross_focus)
    except ValueError:
        idx = 2
    idx = max(0, min(len(CROSS_ORDER) - 1, idx + delta))
    return replace(state, cross_focus=CROSS_ORDER[idx], focus_zone=FocusZone.CONTROLS)


def toggle_focus_zone(state: OverlayState) -> OverlayState:
    zone = FocusZone.TIMELINE if state.focus_zone == FocusZone.CONTROLS else FocusZone.CONTROLS
    return replace(state, focus_zone=zone)


def show_controls(state: OverlayState) -> OverlayState:
    if state.view == View.TRACKS:
        return state
    return replace(state, view=View.CONTROLS)


def show_scrub(state: OverlayState) -> OverlayState:
    return replace(state, view=View.SCRUB, focus_zone=FocusZone.TIMELINE)


def hide_controls(state: OverlayState) -> OverlayState:
    if state.view not in (View.CONTROLS, View.SCRUB):
        return state
    return replace(state, view=View.WATCHING)


def dismiss_controls(state: OverlayState) -> OverlayState:
    scrub = state.scrub
    if scrub is not None:
        scrub = ScrubState(
            scrub_fraction=scrub.scrub_fraction,
            pending_seek_fraction=None,
            time_pos=scrub.time_pos,
            duration=scrub.duration,
        )
    return replace(state, view=View.WATCHING, scrub=scrub)


def open_tracks(state: OverlayState, kind: TrackKind) -> OverlayState:
    return replace(state, view=View.TRACKS, track_kind=kind)


def close_tracks(state: OverlayState) -> OverlayState:
    return replace(state, view=View.CONTROLS)


def selected_track_index(state: OverlayState, sid: int | None, aid: int | None) -> int:
    rows = state.track_rows or []
    selected_id = sid if state.track_kind == TrackKind.SUBTITLES else aid
    for i, (track_id, _label) in enumerate(rows):
        if track_id == selected_id:
            return i
    return 0
