"""Scrub engine tests."""

from __future__ import annotations

import pytest

from lumi.ui.player.controller.scrub_engine import ScrubEngine, ScrubState


def test_start_key_scrub_advances_from_current_position() -> None:
    state = ScrubState(time_pos=45.0, duration=120.0, scrub_fraction=45.0 / 120.0)
    state, seek, debounce = ScrubEngine.start_key_scrub(state, 1)

    assert state.time_pos == 55.0
    assert state.scrub_fraction == pytest.approx(55.0 / 120.0)
    assert seek is not None
    assert seek.fraction == pytest.approx(55.0 / 120.0)
    assert seek.exact is True
    assert debounce is None


def test_start_key_scrub_noop_without_duration() -> None:
    state = ScrubState(time_pos=5.0, duration=0.0)
    state, seek, debounce = ScrubEngine.start_key_scrub(state, 1)

    assert not state.keyboard_scrubbing
    assert not state.key_scrub_dirty
    assert state.time_pos == 5.0
    assert seek is None
    assert debounce is None


def test_stop_key_scrub_skips_finalize_when_not_dirty() -> None:
    state = ScrubState(keyboard_scrubbing=True, scrub_fraction=0.0, duration=120.0)
    state, seek = ScrubEngine.stop_key_scrub(state)

    assert not state.keyboard_scrubbing
    assert seek is None


def test_stop_key_scrub_finalizes_after_dirty_scrub() -> None:
    state = ScrubState(
        keyboard_scrubbing=True,
        scrub_fraction=55.0 / 120.0,
        time_pos=55.0,
        duration=120.0,
        key_scrub_dirty=True,
    )
    state, seek = ScrubEngine.stop_key_scrub(state)

    assert not state.keyboard_scrubbing
    assert seek is not None
    assert seek.fraction == pytest.approx(55.0 / 120.0)
