"""Persisted playback positions keyed by library path."""

from __future__ import annotations

import json
import logging
from pathlib import Path, PurePosixPath

from lumi.infrastructure.paths import watch_progress_path

logger = logging.getLogger(__name__)

RESUME_END_THRESHOLD_SECONDS = 30.0
RESUME_END_THRESHOLD_FRACTION = 0.95
MIN_SAVE_POSITION_SECONDS = 3.0


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
