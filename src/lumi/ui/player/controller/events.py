"""Playback state and Qt signals."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class PlaybackState:
    has_media: bool
    paused: bool
    time_pos: float
    duration: float
    volume: float
    muted: bool
    sid: int | None
    aid: int | None


class PlaybackSignals(QObject):
    state_changed = Signal(object)
    track_list_changed = Signal()
