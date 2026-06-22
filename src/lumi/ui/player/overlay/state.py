"""Overlay view state and transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import PurePosixPath

from lumi.domain.subtitles.browse import BrowseRow
from lumi.domain.video_aspect import VIDEO_ASPECT_MODES
from lumi.ui.player.controller.scrub_engine import ScrubState


class View(str, Enum):
    WATCHING = "watching"
    SCRUB = "scrub"
    CONTROLS = "controls"
    TRACKS = "tracks"
    VIDEO = "video"
    SUBTITLE_BROWSE = "subtitle_browse"


class TrackKind(str, Enum):
    SUBTITLES = "subtitles"
    AUDIO = "audio"


class FocusZone(str, Enum):
    CONTROLS = "controls"
    TIMELINE = "timeline"


CROSS_ORDER = ("m1", "m10", "center", "p10", "p1")


@dataclass(frozen=True)
class TrackRow:
    label: str
    mpv_id: int | None = None
    external_path: PurePosixPath | None = None
    opens_browse: bool = False
    opens_napi_download: bool = False
    show_napi_save: bool = False
    show_napi_delete: bool = False
    is_sub_delay_control: bool = False
    is_action: bool = False


def track_row_focusable(row: TrackRow) -> bool:
    if not row.is_action:
        return True
    return row.opens_napi_download or row.opens_browse or row.is_sub_delay_control


def is_footer_button(row: TrackRow) -> bool:
    return row.opens_napi_download or row.opens_browse


def track_row_actions(row: TrackRow) -> tuple[str, ...]:
    if row.is_sub_delay_control:
        return ()
    actions: list[str] = []
    if row.show_napi_save:
        actions.append("save")
    if row.show_napi_delete:
        actions.append("delete")
    return tuple(actions)


def move_track_action_focus(state: OverlayState, delta: int) -> OverlayState:
    rows = state.track_rows or []
    if not (0 <= state.track_focus < len(rows)):
        return replace(state, track_action_focus=None)
    actions = track_row_actions(rows[state.track_focus])
    if not actions:
        return replace(state, track_action_focus=None)
    current = state.track_action_focus
    if delta > 0:
        if current is None:
            return replace(state, track_action_focus=actions[0])
        try:
            idx = actions.index(current)
        except ValueError:
            return replace(state, track_action_focus=actions[0])
        if idx + 1 < len(actions):
            return replace(state, track_action_focus=actions[idx + 1])
        return state
    if current is None:
        return state
    try:
        idx = actions.index(current)
    except ValueError:
        return replace(state, track_action_focus=None)
    if idx > 0:
        return replace(state, track_action_focus=actions[idx - 1])
    return replace(state, track_action_focus=None)


def move_track_focus(state: OverlayState, delta: int) -> OverlayState:
    rows = state.track_rows or []
    if not rows:
        return replace(state, track_action_focus=None)
    idx = state.track_focus
    step = 1 if delta >= 0 else -1
    for _ in range(len(rows)):
        next_idx = idx + step
        if next_idx < 0 or next_idx >= len(rows):
            break
        idx = next_idx
        if track_row_focusable(rows[idx]):
            return replace(state, track_focus=idx, track_action_focus=None)
    return replace(state, track_action_focus=None)


@dataclass
class OverlayState:
    view: View = View.WATCHING
    focus_zone: FocusZone = FocusZone.CONTROLS
    cross_focus: str = "center"
    track_kind: TrackKind = TrackKind.SUBTITLES
    track_focus: int = 0
    track_action_focus: str | None = None
    scrub: ScrubState | None = None
    volume_flash: bool = False
    volume: float = 100.0
    muted: bool = False
    time_pos: float = 0.0
    duration: float = 0.0
    paused: bool = True
    track_rows: list[TrackRow] | None = None
    browse_path: PurePosixPath | None = None
    browse_rows: list[BrowseRow] | None = None
    browse_focus: int = 0
    video_focus: int = 0
    panel_w: int = 340
    panel_scroll_y: int = 0

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
    if state.view in (View.TRACKS, View.VIDEO, View.SUBTITLE_BROWSE):
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
    return replace(
        state,
        view=View.TRACKS,
        track_kind=kind,
        track_action_focus=None,
        panel_scroll_y=0,
    )


def close_tracks(state: OverlayState) -> OverlayState:
    return replace(state, view=View.CONTROLS, track_action_focus=None)


def open_video(state: OverlayState, *, focus_index: int = 0) -> OverlayState:
    return replace(state, view=View.VIDEO, video_focus=focus_index, panel_scroll_y=0)


def close_video(state: OverlayState) -> OverlayState:
    return replace(state, view=View.CONTROLS)


def move_video_focus(state: OverlayState, delta: int) -> OverlayState:
    count = len(VIDEO_ASPECT_MODES)
    if count == 0:
        return state
    idx = max(0, min(count - 1, state.video_focus + delta))
    return replace(state, video_focus=idx)


def open_subtitle_browse(state: OverlayState) -> OverlayState:
    return replace(state, view=View.SUBTITLE_BROWSE, browse_focus=0, panel_scroll_y=0)


def close_subtitle_browse(state: OverlayState) -> OverlayState:
    return replace(
        state,
        view=View.TRACKS,
        browse_path=None,
        browse_rows=None,
        browse_focus=0,
    )


def selected_track_index(state: OverlayState, sid: int | None, aid: int | None) -> int:
    rows = state.track_rows or []
    selected_id = sid if state.track_kind == TrackKind.SUBTITLES else aid
    for i, row in enumerate(rows):
        if row.mpv_id == selected_id and row.external_path is None:
            return i
    return 0
