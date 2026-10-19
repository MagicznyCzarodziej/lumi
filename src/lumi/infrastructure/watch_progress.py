"""Persisted playback positions keyed by library path."""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from lumi.domain.recent_watch import RecentWatchRecord, is_resumable_position
from lumi.infrastructure.paths import recent_watch_path, watch_progress_path

logger = logging.getLogger(__name__)

RESUME_END_THRESHOLD_SECONDS = 30.0
RESUME_END_THRESHOLD_FRACTION = 0.95
MIN_SAVE_POSITION_SECONDS = 3.0
RECENT_WATCH_SCHEMA_VERSION = 1


def _path_key(library_path: PurePosixPath) -> str:
    return library_path.as_posix()


def _is_near_end(position: float, duration: float | None) -> bool:
    if duration is not None and duration > 0:
        if position >= duration - RESUME_END_THRESHOLD_SECONDS:
            return True
        if position >= duration * RESUME_END_THRESHOLD_FRACTION:
            return True
    return False


def _should_persist(position: float, duration: float | None) -> bool:
    if position < MIN_SAVE_POSITION_SECONDS:
        return False
    return not _is_near_end(position, duration)


def load_watch_position(
    library_path: PurePosixPath,
    *,
    duration: float | None = None,
    path: Path | None = None,
) -> float | None:
    progress_path = path or watch_progress_path()

    if not progress_path.is_file():
        return None

    try:
        with progress_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read watch progress from %s: %s", progress_path, exc)
        return None

    if not isinstance(data, dict):
        return None

    raw_position = data.get(_path_key(library_path))
    if raw_position is None:
        return None

    try:
        position = float(raw_position)
    except (TypeError, ValueError):
        return None

    if position < MIN_SAVE_POSITION_SECONDS:
        return None
    if _is_near_end(position, duration):
        return None
    return position


def save_watch_position(
    library_path: PurePosixPath,
    position: float,
    *,
    duration: float | None = None,
    path: Path | None = None,
) -> None:
    progress_path = path or watch_progress_path()
    key = _path_key(library_path)

    try:
        if progress_path.is_file():
            with progress_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                data = {}
        else:
            data = {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read watch progress from %s: %s", progress_path, exc)
        data = {}

    if not _should_persist(position, duration):
        if key in data:
            del data[key]
    else:
        data[key] = round(position, 3)

    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        with progress_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        logger.warning("Could not save watch progress to %s: %s", progress_path, exc)


def load_recent_watch_records(*, path: Path | None = None) -> list[RecentWatchRecord]:
    """Load valid recent-watch records from the versioned local store."""
    records_path = path or recent_watch_path()
    if not records_path.is_file():
        return []

    try:
        with records_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read recent watch records from %s: %s", records_path, exc)
        return []

    if (
        not isinstance(data, dict)
        or data.get("version") != RECENT_WATCH_SCHEMA_VERSION
        or not isinstance(data.get("records"), list)
    ):
        return []

    return [
        record
        for raw_record in data["records"]
        if (record := _decode_recent_watch_record(raw_record)) is not None
    ]


def save_recent_watch_record(
    library_path: PurePosixPath,
    position: float,
    *,
    duration: float | None = None,
    watched_at: datetime | None = None,
    path: Path | None = None,
) -> None:
    """Save a recently watched record, or remove it when no resume is possible."""
    records_path = path or recent_watch_path()
    records = [
        record
        for record in load_recent_watch_records(path=records_path)
        if record.library_path != library_path
    ]

    if is_resumable_position(position, duration):
        try:
            records.append(
                RecentWatchRecord(
                    library_path=library_path,
                    position=position,
                    duration=duration,
                    watched_at=watched_at or datetime.now(UTC),
                )
            )
        except ValueError as exc:
            logger.warning(
                "Could not create recent watch record for %s: %s",
                library_path,
                exc,
            )
            return

    payload = {
        "version": RECENT_WATCH_SCHEMA_VERSION,
        "records": [_encode_recent_watch_record(record) for record in records],
    }
    _write_recent_watch_payload(records_path, payload)


def _decode_recent_watch_record(raw_record: object) -> RecentWatchRecord | None:
    if not isinstance(raw_record, dict):
        return None

    raw_path = raw_record.get("path")
    raw_position = raw_record.get("position")
    raw_duration = raw_record.get("duration")
    raw_watched_at = raw_record.get("watchedAt")
    if (
        not isinstance(raw_path, str)
        or not raw_path
        or not isinstance(raw_watched_at, str)
    ):
        return None

    position = _as_float(raw_position)
    if position is None:
        return None
    duration = None if raw_duration is None else _as_float(raw_duration)
    if raw_duration is not None and duration is None:
        return None

    try:
        watched_at = datetime.fromisoformat(raw_watched_at.replace("Z", "+00:00"))
        record = RecentWatchRecord(
            library_path=PurePosixPath(raw_path),
            position=position,
            duration=duration,
            watched_at=watched_at,
        )
    except ValueError:
        return None
    return record if is_resumable_position(record.position, record.duration) else None


def _encode_recent_watch_record(record: RecentWatchRecord) -> dict[str, object]:
    payload: dict[str, object] = {
        "path": record.library_path.as_posix(),
        "position": record.position,
        "watchedAt": record.watched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if record.duration is not None:
        payload["duration"] = record.duration
    return payload


def _write_recent_watch_payload(path: Path, payload: dict[str, object]) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    except OSError as exc:
        logger.warning("Could not save recent watch records to %s: %s", path, exc)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _as_float(value: object) -> float | None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None
    return float(value)
