"""Tests for recently watched domain resolution."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pathlib import Path, PurePosixPath

from lumi.domain.library.serialization.from_json import library_from_json
from lumi.domain.recent_watch import (
    RecentWatchRecord,
    coerce_saved_playback_position,
    is_playback_complete,
    is_recent_watch_record,
    is_resumable_position,
    resolve_recent_watch_records,
    resume_timeline_fraction,
    resume_timeline_percent,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/lumi/infrastructure/mock/fixtures/mock_library.json"
)


def test_coerce_saved_playback_position_keeps_completed_sessions() -> None:
    assert coerce_saved_playback_position(0.0, 0.0, 7200.0) == 0.0
    assert coerce_saved_playback_position(0.0, 7190.0, 7200.0) == 7190.0
    assert coerce_saved_playback_position(0.0, 7200.0, 7200.0) == 7200.0
    assert coerce_saved_playback_position(2.0, 6840.0, 7200.0) == 6840.0


def test_resume_timeline_fraction_is_position_over_duration_not_watch_time() -> None:
    assert resume_timeline_fraction(3600.0, 7200.0) == 0.5
    assert resume_timeline_fraction(7190.0, 7200.0) == pytest.approx(7190.0 / 7200.0)
    assert resume_timeline_percent(240.0, 3600.0) == 6
    assert resume_timeline_percent(7190.0, 7200.0) == 100
    assert resume_timeline_fraction(120.0, None) is None


def test_recent_watch_includes_completed_but_resume_excludes_it() -> None:
    duration = 7200.0
    position = 7190.0
    assert not is_resumable_position(position, duration)
    assert is_playback_complete(position, duration)
    assert is_recent_watch_record(position, duration)


def test_resolve_recent_watch_records_uses_current_library_and_recency() -> None:
    library = library_from_json(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 18, 19, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Removed/Film.mkv"),
            position=300.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 21, 0, tzinfo=UTC),
        ),
    ]

    resolved = resolve_recent_watch_records(records, library)

    assert [
        (item.entry.name.name, item.episode.name.name if item.episode else None)
        for item in resolved
    ] == [("Band of Brothers", "S01E02"), ("Alien", None)]
    assert [item.library_path for item in resolved] == [
        PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
        PurePosixPath("Alien/Alien.mkv"),
    ]
    assert [
        (item.playable_name.name, item.episodes_group.id.id if item.episodes_group else None)
        for item in resolved
    ] == [("S01E02", "bob-s1"), ("Alien", None)]


def test_resolve_recent_watch_records_includes_completed_records() -> None:
    library = library_from_json(FIXTURE_PATH.read_text(encoding="utf-8"))
    completed = RecentWatchRecord(
        library_path=PurePosixPath("Alien/Alien.mkv"),
        position=7190.0,
        duration=7200.0,
        watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
    )

    resolved = resolve_recent_watch_records([completed], library)

    assert len(resolved) == 1
    assert resolved[0].library_path == PurePosixPath("Alien/Alien.mkv")
    assert resolved[0].position == 7190.0
