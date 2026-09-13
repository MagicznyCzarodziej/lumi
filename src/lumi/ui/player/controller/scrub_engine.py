"""Debounced seek and key-scrub ramp logic (no Qt dependencies)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeekCommand:
    fraction: float
    exact: bool


@dataclass
class ScrubState:
    scrub_fraction: float = 0.0
    pending_seek_fraction: float | None = None
    time_pos: float = 0.0
    duration: float = 0.0
    keyboard_scrubbing: bool = False
    key_scrub_direction: int = 0
    key_scrub_elapsed_ms: int = 0
    key_scrub_dirty: bool = False
    seek_dragging: bool = False

    def is_scrubbing(self) -> bool:
        return self.seek_dragging or self.keyboard_scrubbing


class ScrubEngine:
    MIN_STEP_S = 1.5
    MAX_STEP_S = 55.0
    RAMP_MS = 2800
    SEEK_DEBOUNCE_MS = 40
    KEY_SCRUB_SEEK_MS = 120
    INITIAL_KEY_SCRUB_S = 5.0

    @staticmethod
    def fraction_at(pos_x: float, inner_x: float, inner_width: float) -> float:
        if inner_width <= 0:
            return 0.0
        return max(0.0, min(1.0, (pos_x - inner_x) / inner_width))

    @classmethod
    def key_scrub_step_seconds(cls, elapsed_ms: int) -> float:
        ramp = max(1, cls.RAMP_MS)
        t = min(1.0, elapsed_ms / ramp)
        eased = t * t * t
        return cls.MIN_STEP_S + eased * (cls.MAX_STEP_S - cls.MIN_STEP_S)

    @classmethod
    def scrub_to_fraction(
        cls,
        state: ScrubState,
        fraction: float,
        *,
        immediate: bool = False,
        sync_player: bool = True,
    ) -> tuple[ScrubState, SeekCommand | None, int | None]:
        """Update scrub state. Returns (state, immediate seek, debounce ms)."""
        fraction = max(0.0, min(1.0, fraction))
        state.scrub_fraction = fraction
        state.pending_seek_fraction = fraction
        if state.duration > 0:
            state.time_pos = fraction * state.duration

        if not sync_player:
            return state, None, cls.KEY_SCRUB_SEEK_MS

        if immediate:
            cmd = SeekCommand(fraction=fraction, exact=True)
            state.pending_seek_fraction = None
            return state, cmd, None

        cmd = SeekCommand(fraction=fraction, exact=False)
        state.pending_seek_fraction = None
        return state, cmd, cls.SEEK_DEBOUNCE_MS

    @classmethod
    def scrub_by_seconds(
        cls,
        state: ScrubState,
        delta: float,
        *,
        immediate: bool = False,
        sync_player: bool = True,
    ) -> tuple[ScrubState, SeekCommand | None, int | None]:
        if state.duration <= 0:
            return state, None, None
        target = max(0.0, min(state.duration, state.time_pos + delta))
        return cls.scrub_to_fraction(
            state,
            target / state.duration,
            immediate=immediate,
            sync_player=sync_player,
        )

    @classmethod
    def start_key_scrub(
        cls, state: ScrubState, direction: int
    ) -> tuple[ScrubState, SeekCommand | None, int | None]:
        if state.duration <= 0:
            return state, None, None
        state.keyboard_scrubbing = True
        state.key_scrub_direction = direction
        state.key_scrub_elapsed_ms = 0
        state.key_scrub_dirty = False
        state, seek, debounce = cls.scrub_by_seconds(
            state,
            direction * cls.INITIAL_KEY_SCRUB_S,
            immediate=True,
        )
        if seek is not None:
            state.key_scrub_dirty = True
        return state, seek, debounce

    @classmethod
    def key_scrub_tick(cls, state: ScrubState) -> tuple[ScrubState, SeekCommand | None, int | None]:
        if not state.keyboard_scrubbing:
            return state, None, None
        delta = state.key_scrub_direction * cls.key_scrub_step_seconds(state.key_scrub_elapsed_ms)
        prev_fraction = state.scrub_fraction
        state, seek, debounce = cls.scrub_by_seconds(state, delta, sync_player=False)
        if state.scrub_fraction != prev_fraction:
            state.key_scrub_dirty = True
        return state, seek, debounce

    @classmethod
    def finish_scrub(cls, state: ScrubState, *, force: bool = False) -> tuple[ScrubState, SeekCommand | None]:
        if state.duration <= 0:
            state.pending_seek_fraction = None
            return state, None
        if not force and not state.key_scrub_dirty:
            state.pending_seek_fraction = None
            return state, None
        fraction = state.scrub_fraction
        if state.duration > 0:
            state.time_pos = fraction * state.duration
        state.pending_seek_fraction = None
        return state, SeekCommand(fraction=fraction, exact=True)

    @classmethod
    def apply_pending(cls, state: ScrubState) -> tuple[ScrubState, SeekCommand | None]:
        if state.pending_seek_fraction is None:
            return state, None
        fraction = state.pending_seek_fraction
        state.pending_seek_fraction = None
        return state, SeekCommand(fraction=fraction, exact=False)

    @classmethod
    def stop_key_scrub(
        cls, state: ScrubState, *, finalize: bool = True
    ) -> tuple[ScrubState, SeekCommand | None]:
        if not state.keyboard_scrubbing:
            return state, None
        state.keyboard_scrubbing = False
        state.key_scrub_direction = 0
        if finalize and state.key_scrub_dirty:
            state, seek = cls.finish_scrub(state)
            state.key_scrub_dirty = False
            return state, seek
        state.key_scrub_dirty = False
        return state, None
