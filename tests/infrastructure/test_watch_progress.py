"""Tests for persisted watch progress."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import PurePosixPath

from lumi.domain.recent_watch import RecentWatchRecord
from lumi.infrastructure.watch_history import JsonWatchHistory
from lumi.infrastructure.watch_progress import (
    load_recent_watch_records,
    load_watch_position,
    save_recent_watch_record,
    save_watch_position,
)


def test_load_watch_position_returns_none_when_missing(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    assert load_watch_position(library_path, path=path) is None


def test_save_and_load_watch_position(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 1234.567, duration=7200.0, path=path)

    assert load_watch_position(library_path, duration=7200.0, path=path) == 1234.567
    assert json.loads(path.read_text(encoding="utf-8")) == {"/Movies/Alien/Alien.mkv": 1234.567}


def test_save_watch_position_does_not_persist_near_start(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 2.0, duration=7200.0, path=path)

    assert not path.exists() or load_watch_position(library_path, duration=7200.0, path=path) is None


def test_save_watch_position_clears_near_end(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")

    save_watch_position(library_path, 1000.0, duration=7200.0, path=path)
    save_watch_position(library_path, 7180.0, duration=7200.0, path=path)

    assert load_watch_position(library_path, duration=7200.0, path=path) is None
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_load_watch_position_rejects_near_end_for_known_duration(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("/Movies/Alien/Alien.mkv")
    path.write_text(json.dumps({"/Movies/Alien/Alien.mkv": 7000.0}), encoding="utf-8")

    assert load_watch_position(library_path, duration=7200.0, path=path) is None


def test_save_watch_position_updates_existing_entry(tmp_path) -> None:
    path = tmp_path / "watch_progress.json"
    first = PurePosixPath("/Movies/Alien/Alien.mkv")
    second = PurePosixPath("/Movies/Blade Runner/Blade Runner.mkv")

    save_watch_position(first, 100.0, duration=7200.0, path=path)
    save_watch_position(second, 200.0, duration=7200.0, path=path)
    save_watch_position(first, 150.0, duration=7200.0, path=path)

    assert load_watch_position(first, duration=7200.0, path=path) == 150.0
    assert load_watch_position(second, duration=7200.0, path=path) == 200.0


def test_save_and_load_recent_watch_record(tmp_path) -> None:
    path = tmp_path / "recent_watch.json"
    library_path = PurePosixPath("Alien/Alien.mkv")
    watched_at = datetime(2026, 10, 19, 21, 16, tzinfo=UTC)

    save_recent_watch_record(
        library_path,
        1234.567,
        duration=7200.0,
        watched_at=watched_at,
        path=path,
    )

    assert load_recent_watch_records(path=path) == [
        RecentWatchRecord(
            library_path=library_path,
            position=1234.567,
            duration=7200.0,
            watched_at=watched_at,
        )
    ]
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "records": [
            {
                "path": "Alien/Alien.mkv",
                "position": 1234.567,
                "duration": 7200.0,
                "watchedAt": "2026-10-19T21:16:00Z",
            }
        ],
    }


def test_save_recent_watch_record_removes_completed_playback(tmp_path) -> None:
    path = tmp_path / "recent_watch.json"
    library_path = PurePosixPath("Alien/Alien.mkv")

    save_recent_watch_record(library_path, 100.0, duration=7200.0, path=path)
    save_recent_watch_record(library_path, 7190.0, duration=7200.0, path=path)

    assert load_recent_watch_records(path=path) == []


def test_load_recent_watch_records_ignores_corrupt_or_unknown_schema(tmp_path) -> None:
    recent_path = tmp_path / "recent_watch.json"
    watch_progress = tmp_path / "watch_progress.json"
    library_path = PurePosixPath("Alien/Alien.mkv")
    watch_progress.write_text(json.dumps({library_path.as_posix(): 120.0}), encoding="utf-8")
    recent_path.write_text("{", encoding="utf-8")

    assert load_recent_watch_records(path=recent_path) == []
    assert load_watch_position(library_path, duration=7200.0, path=watch_progress) == 120.0

    recent_path.write_text(
        json.dumps({"version": 2, "records": []}),
        encoding="utf-8",
    )

    assert load_recent_watch_records(path=recent_path) == []


def test_load_recent_watch_records_ignores_malformed_and_completed_records(tmp_path) -> None:
    path = tmp_path / "recent_watch.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "records": [
                    {
                        "path": "Alien/Alien.mkv",
                        "position": 100.0,
                        "duration": 7200.0,
                        "watchedAt": "2026-10-19T21:16:00Z",
                    },
                    {
                        "path": "invalid/record.mkv",
                        "position": "not-a-number",
                        "watchedAt": "2026-10-19T21:16:00Z",
                    },
                    {
                        "path": "Complete/Film.mkv",
                        "position": 7190.0,
                        "duration": 7200.0,
                        "watchedAt": "2026-10-19T21:16:00Z",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert load_recent_watch_records(path=path) == [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=100.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 21, 16, tzinfo=UTC),
        )
    ]


def test_watch_history_port_records_resume_and_recent_entry_with_shared_policy(tmp_path) -> None:
    progress_path = tmp_path / "watch_progress.json"
    recent_path = tmp_path / "recent_watch.json"
    library_path = PurePosixPath("Alien/Alien.mkv")
    history = JsonWatchHistory(
        progress_path=progress_path,
        recent_path=recent_path,
    )

    history.record_playback(library_path, 120.0, duration=7200.0)

    assert history.resume_position(library_path, duration=7200.0) == 120.0
    assert [record.library_path for record in history.recent_entries()] == [library_path]

    history.record_playback(library_path, 7190.0, duration=7200.0)

    assert history.resume_position(library_path, duration=7200.0) is None
    assert history.recent_entries() == []
