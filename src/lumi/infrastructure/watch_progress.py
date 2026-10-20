"""Persisted playback positions keyed by library path."""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from lumi.domain.recent_watch import (
    MIN_SAVE_POSITION_SECONDS,
    RecentWatchRecord,
    is_recent_watch_record,
    is_resumable_position,
)
from lumi.infrastructure.paths import recent_watch_path, watch_progress_path

logger = logging.getLogger(__name__)

RECENT_WATCH_SCHEMA_VERSION = 1
_LEGACY_BOOTSTRAP_WINDOW = timedelta(seconds=2)


def _path_key(library_path: PurePosixPath) -> str:
    return library_path.as_posix()


def _decode_progress_entry(raw: object) -> tuple[float | None, datetime | None]:
    if isinstance(raw, bool):
        return None, None
    if isinstance(raw, int | float):
        return float(raw), None
    if not isinstance(raw, dict):
        return None, None
    position = _as_float(raw.get("position"))
    if position is None:
        return None, None
    raw_watched_at = raw.get("watchedAt")
    if not isinstance(raw_watched_at, str):
        return position, None
    try:
        watched_at = datetime.fromisoformat(raw_watched_at.replace("Z", "+00:00"))
    except ValueError:
        return position, None
    return position, watched_at


def _encode_progress_entry(position: float, watched_at: datetime) -> dict[str, object]:
    return {
        "position": round(position, 3),
        "watchedAt": watched_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }


def _drop_legacy_bulk_bootstrap_records(
    records: list[RecentWatchRecord],
) -> list[RecentWatchRecord]:
    """Remove one-shot migration dumps that share the same second and look like resume bookmarks."""
    if len(records) < 10:
        return records
    watched_times = [record.watched_at for record in records]
    if max(watched_times) - min(watched_times) > _LEGACY_BOOTSTRAP_WINDOW:
        return records
    return []


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

    raw_entry = data.get(_path_key(library_path))
    if raw_entry is None:
        return None

    position, _watched_at = _decode_progress_entry(raw_entry)
    if position is None:
        return None

    if not is_resumable_position(position, duration):
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

    if not is_resumable_position(position, duration):
        if key in data:
            del data[key]
    else:
        data[key] = _encode_progress_entry(position, datetime.now(UTC))

    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        with progress_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        logger.warning("Could not save watch progress to %s: %s", progress_path, exc)


def clear_watch_progress(
    library_path: PurePosixPath,
    *,
    path: Path | None = None,
) -> None:
    """Remove a saved resume bookmark for a library video."""
    progress_path = path or watch_progress_path()
    key = _path_key(library_path)

    try:
        if not progress_path.is_file():
            return
        with progress_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or key not in data:
            return
        del data[key]
        if data:
            with progress_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
        else:
            progress_path.unlink(missing_ok=True)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not clear watch progress in %s: %s", progress_path, exc)


def remove_recent_watch_record(
    library_path: PurePosixPath,
    *,
    path: Path | None = None,
) -> None:
    """Remove one title from the Recently watched store."""
    records_path = path or recent_watch_path()
    loaded = load_recent_watch_records(path=records_path)
    records = [record for record in loaded if record.library_path != library_path]
    if len(records) == len(loaded):
        return
    if records:
        _rewrite_recent_watch_records(records_path, records)
    else:
        records_path.unlink(missing_ok=True)


def forget_playback(
    library_path: PurePosixPath,
    *,
    progress_path: Path | None = None,
    recent_path: Path | None = None,
) -> None:
    """Clear resume progress and drop the entry from Recently watched."""
    clear_watch_progress(library_path, path=progress_path)
    remove_recent_watch_record(library_path, path=recent_path)


def bootstrap_recent_watch_from_progress(
    *,
    progress_path: Path | None = None,
    recent_path: Path | None = None,
) -> bool:
    """Fill recent-watch store from watch progress when recent data was never written."""
    records_path = recent_path or recent_watch_path()
    if records_path.is_file():
        try:
            with records_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if (
                isinstance(data, dict)
                and data.get("version") == RECENT_WATCH_SCHEMA_VERSION
                and isinstance(data.get("records"), list)
                and data["records"]
            ):
                return False
        except (OSError, json.JSONDecodeError):
            pass

    progress_file = progress_path or watch_progress_path()
    if not progress_file.is_file():
        return False

    try:
        with progress_file.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read watch progress from %s: %s", progress_file, exc)
        return False

    if not isinstance(data, dict) or not data:
        return False

    progress_mtime = datetime.fromtimestamp(progress_file.stat().st_mtime, UTC)
    migrated = False
    items = list(data.items())
    for index, (raw_path, raw_entry) in enumerate(items):
        if not isinstance(raw_path, str) or not raw_path:
            continue
        position, watched_at = _decode_progress_entry(raw_entry)
        if position is None or not is_recent_watch_record(position, None):
            continue
        if watched_at is None:
            watched_at = progress_mtime - timedelta(seconds=len(items) - index)
        save_recent_watch_record(
            PurePosixPath(raw_path),
            position,
            duration=None,
            watched_at=watched_at,
            path=records_path,
        )
        migrated = True
    return migrated


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

    records = [
        record
        for raw_record in data["records"]
        if (record := _decode_recent_watch_record(raw_record)) is not None
    ]
    pruned = _drop_legacy_bulk_bootstrap_records(records)
    if len(pruned) != len(records):
        if pruned:
            _rewrite_recent_watch_records(records_path, pruned)
        else:
            records_path.unlink(missing_ok=True)
        records = pruned
    records.sort(key=lambda record: record.watched_at, reverse=True)
    return records


def _rewrite_recent_watch_records(path: Path, records: list[RecentWatchRecord]) -> None:
    payload = {
        "version": RECENT_WATCH_SCHEMA_VERSION,
        "records": [_encode_recent_watch_record(record) for record in records],
    }
    _write_recent_watch_payload(path, payload)


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
    loaded = load_recent_watch_records(path=records_path)
    previous = next(
        (record for record in loaded if record.library_path == library_path),
        None,
    )
    records = [record for record in loaded if record.library_path != library_path]
    merged_duration = duration
    if previous is not None and previous.duration is not None:
        if merged_duration is None:
            merged_duration = previous.duration
        else:
            merged_duration = max(previous.duration, merged_duration)

    if is_recent_watch_record(position, merged_duration):
        try:
            records.append(
                RecentWatchRecord(
                    library_path=library_path,
                    position=position,
                    duration=merged_duration,
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
    elif (
        previous is not None
        and is_recent_watch_record(previous.position, previous.duration or merged_duration)
        and position < MIN_SAVE_POSITION_SECONDS
    ):
        records.append(previous)

    records.sort(key=lambda record: record.watched_at, reverse=True)
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
    return record if is_recent_watch_record(record.position, record.duration) else None


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
