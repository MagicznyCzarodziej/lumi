"""Tests for recently watched domain resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from lumi.domain.library.serialization.from_json import library_from_json
from lumi.domain.recent_watch import RecentWatchRecord, resolve_recent_watch_records

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/lumi/infrastructure/mock/fixtures/mock_library.json"
)


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


def test_resolve_recent_watch_records_ignores_completed_records() -> None:
    library = library_from_json(FIXTURE_PATH.read_text(encoding="utf-8"))
    completed = RecentWatchRecord(
        library_path=PurePosixPath("Alien/Alien.mkv"),
        position=7190.0,
        duration=7200.0,
        watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
    )

    assert resolve_recent_watch_records([completed], library) == []
