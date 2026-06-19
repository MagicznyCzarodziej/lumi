"""Thin wrapper over mpv properties/commands for the overlay."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer

from lumi.infrastructure.player_preferences import save_player_volume
from lumi.ui.player.controller.events import PlaybackSignals, PlaybackState
from lumi.ui.player.controller.track_labels import audio_track_label, subtitle_track_label
from lumi.ui.player.platform.mpv_loader import get_mpv


class MpvController:
    """Thin wrapper over mpv properties/commands for the overlay."""

    @staticmethod
    def coerce_pause(val, default: bool = True) -> bool:
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.lower() in ("yes", "true", "1", "on")
        return default

    def __init__(self, mpv_getter: Callable[[], object | None]):
        self._mpv_getter = mpv_getter
        self.signals = PlaybackSignals()
        self._bound = False
        self._emit_scheduled = False
        self._time_pos_emit_pending = False
        self._state = PlaybackState(
            has_media=False,
            paused=True,
            time_pos=0.0,
            duration=0.0,
            volume=100.0,
            muted=False,
            sid=None,
            aid=None,
        )

    @property
    def state(self) -> PlaybackState:
        return self._state

    def _mpv(self):
        return self._mpv_getter()

    def _safe(self, fn, default=None):
        try:
            return fn()
        except (AttributeError, get_mpv().ShutdownError, SystemError, OSError, ValueError):
            return default

    def _emit_state(self):
        self.signals.state_changed.emit(self._state)

    def _schedule_emit(self):
        if self._emit_scheduled:
            return
        self._emit_scheduled = True
        QTimer.singleShot(0, self._flush_emit)

    def _flush_emit(self):
        self._emit_scheduled = False
        self._emit_state()

    def _schedule_time_pos_emit(self):
        if self._time_pos_emit_pending:
            return
        self._time_pos_emit_pending = True
        QTimer.singleShot(16, self._flush_time_pos_emit)

    def _flush_time_pos_emit(self):
        self._time_pos_emit_pending = False
        self._emit_state()

    def _refresh_state(self):
        self._state = PlaybackState(
            has_media=self.has_media(),
            paused=self.is_paused(),
            time_pos=self.time_pos(),
            duration=self.duration(),
            volume=self.volume(),
            muted=self.is_muted(),
            sid=self.current_sid(),
            aid=self.current_aid(),
        )
        self._emit_state()

    def bind(self):
        if self._bound:
            return
        player = self._mpv()
        if player is None:
            return
        self._bound = True
        self._refresh_state()

        @player.property_observer("pause")
        def _on_pause(_name, val):
            paused = self.coerce_pause(val, default=True)
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=paused,
                time_pos=self._state.time_pos,
                duration=self._state.duration,
                volume=self._state.volume,
                muted=self._state.muted,
                sid=self._state.sid,
                aid=self._state.aid,
            )
            QTimer.singleShot(0, self._schedule_emit)

        @player.property_observer("time-pos")
        def _on_time_pos(_name, val):
            pos = float(val) if val is not None else 0.0
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=self._state.paused,
                time_pos=pos,
                duration=self._state.duration,
                volume=self._state.volume,
                muted=self._state.muted,
                sid=self._state.sid,
                aid=self._state.aid,
            )
            QTimer.singleShot(0, self._schedule_time_pos_emit)

        @player.property_observer("duration")
        def _on_duration(_name, val):
            dur = float(val) if val is not None else 0.0
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=self._state.paused,
                time_pos=self._state.time_pos,
                duration=dur,
                volume=self._state.volume,
                muted=self._state.muted,
                sid=self._state.sid,
                aid=self._state.aid,
            )
            QTimer.singleShot(0, self._schedule_emit)

        @player.property_observer("volume")
        def _on_volume(_name, val):
            vol = float(val if val is not None else 100)
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=self._state.paused,
                time_pos=self._state.time_pos,
                duration=self._state.duration,
                volume=vol,
                muted=self._state.muted,
                sid=self._state.sid,
                aid=self._state.aid,
            )
            QTimer.singleShot(0, self._schedule_emit)

        @player.property_observer("mute")
        def _on_mute(_name, val):
            muted = self.coerce_pause(val, default=False)
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=self._state.paused,
                time_pos=self._state.time_pos,
                duration=self._state.duration,
                volume=self._state.volume,
                muted=muted,
                sid=self._state.sid,
                aid=self._state.aid,
            )
            QTimer.singleShot(0, self._schedule_emit)

        @player.property_observer("track-list")
        def _on_track_list(_name, _val):
            self._state = PlaybackState(
                has_media=self._state.has_media,
                paused=self._state.paused,
                time_pos=self._state.time_pos,
                duration=self._state.duration,
                volume=self._state.volume,
                muted=self._state.muted,
                sid=self.current_sid(),
                aid=self.current_aid(),
            )
            QTimer.singleShot(0, self.signals.track_list_changed.emit)

        @player.property_observer("path")
        def _on_path(_name, _val):
            self._refresh_state()

    def unbind(self):
        self._bound = False

    def notify_media_loaded(self):
        self._refresh_state()

    def has_media(self) -> bool:
        player = self._mpv()
        if player is None:
            return False

        def check():
            if player.idle_active:
                return False
            path = player.path
            return bool(path)

        return bool(self._safe(check, False))

    def _tracks(self) -> list[dict]:
        player = self._mpv()
        if player is None:
            return []
        try:
            tracks = player.track_list
            return tracks if tracks else []
        except (AttributeError, get_mpv().ShutdownError):
            return []

    def is_paused(self) -> bool:
        player = self._mpv()
        if player is None:
            return True
        val = self._safe(lambda: player.pause, True)
        return self.coerce_pause(val, default=True)

    def is_playing(self) -> bool:
        return self.has_media() and not self.is_paused()

    def toggle_pause(self):
        if not self.has_media():
            return
        player = self._mpv()
        if player is None:
            return
        self._safe(lambda: player.cycle("pause"))

    def _seek_async(self, amount: float, reference: str, precision: str) -> None:
        player = self._mpv()
        if player is None:
            return

        def do_seek():
            p = self._mpv()
            if p is None:
                return
            self._safe(lambda: p.command_async("seek", amount, reference, precision))

        QTimer.singleShot(0, do_seek)

    def seek_relative(self, seconds: float):
        if not self.has_media():
            return
        if self._mpv() is None:
            return
        precision = "exact" if abs(seconds) <= 10 else "keyframes"
        self._seek_async(seconds, "relative", precision)

    def seek_fraction(self, fraction: float, *, exact: bool = False):
        if not self.has_media():
            return
        dur = self.duration()
        if dur <= 0:
            return
        if self._mpv() is None:
            return
        target = max(0.0, min(1.0, fraction)) * dur
        precision = "exact" if exact else "keyframes"
        self._seek_async(target, "absolute", precision)

    def time_pos(self) -> float:
        player = self._mpv()
        if player is None:
            return 0.0
        val = self._safe(lambda: player.time_pos, None)
        return float(val) if val is not None else 0.0

    def duration(self) -> float:
        player = self._mpv()
        if player is None:
            return 0.0
        val = self._safe(lambda: player.duration, None)
        return float(val) if val is not None else 0.0

    def volume(self) -> float:
        player = self._mpv()
        if player is None:
            return 100.0
        val = self._safe(lambda: player.volume, 100)
        return float(val if val is not None else 100)

    def is_muted(self) -> bool:
        player = self._mpv()
        if player is None:
            return False
        val = self._safe(lambda: player.mute, False)
        return self.coerce_pause(val, default=False)

    def toggle_mute(self):
        if not self.has_media():
            return
        player = self._mpv()
        if player is None:
            return
        self._safe(lambda: player.cycle("mute"))

    def change_volume(self, delta: float):
        self.set_volume(self.volume() + delta)

    def set_volume(self, value: float):
        player = self._mpv()
        if player is None:
            return
        clamped = max(0, min(100, round(value)))
        self._safe(lambda: setattr(player, "volume", clamped))
        save_player_volume(clamped)

    def subtitle_tracks(self) -> list[tuple[int | None, str]]:
        rows: list[tuple[int | None, str]] = [(None, "Off")]
        for track in self._tracks():
            if track.get("type") != "sub":
                continue
            tid = track.get("id")
            rows.append((tid, subtitle_track_label(track)))
        return rows or [(None, "Off")]

    def current_subtitle_label(self) -> str:
        sid = self.current_sid()
        for track_id, label in self.subtitle_tracks():
            if track_id == sid:
                return label
        return "Off"

    def audio_tracks(self) -> list[tuple[int | None, str]]:
        rows: list[tuple[int | None, str]] = []
        for track in self._tracks():
            if track.get("type") != "audio":
                continue
            tid = track.get("id")
            rows.append((tid, audio_track_label(track)))
        return rows or [(None, "Default")]

    def current_audio_label(self) -> str:
        aid = self.current_aid()
        rows = self.audio_tracks()
        if aid is not None:
            for track_id, label in rows:
                if track_id == aid:
                    return label
        for track in self._tracks():
            if track.get("type") == "audio" and track.get("default"):
                return audio_track_label(track)
        if rows:
            return rows[0][1]
        return "Default"

    def current_sid(self) -> int | None:
        player = self._mpv()
        if player is None:
            return None
        try:
            sid = player.sid
            if sid in (None, "no", "auto"):
                return None
            return int(sid)
        except (AttributeError, get_mpv().ShutdownError, TypeError, ValueError):
            return None

    def current_aid(self) -> int | None:
        player = self._mpv()
        if player is None:
            return None
        try:
            aid = player.aid
            if aid in (None, "auto"):
                return None
            return int(aid)
        except (AttributeError, get_mpv().ShutdownError, TypeError, ValueError):
            return None

    def set_sid(self, track_id: int | None):
        player = self._mpv()
        if player is None:
            return
        try:
            player.sid = "no" if track_id is None else track_id
        except (AttributeError, get_mpv().ShutdownError):
            pass

    def set_aid(self, track_id: int | None):
        player = self._mpv()
        if player is None:
            return
        try:
            if track_id is not None:
                player.aid = track_id
        except (AttributeError, get_mpv().ShutdownError):
            pass
