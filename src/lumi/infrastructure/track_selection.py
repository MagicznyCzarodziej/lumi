"""Persisted subtitle and audio track selection keyed by library path."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from lumi.infrastructure.paths import track_selection_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SavedTrackSelection:
    aid: int | None = None
    sid: int | None = None
    subtitle_off: bool = False
    subtitle_label: str | None = None
    subtitle_path: PurePosixPath | None = None


def _path_key(library_path: PurePosixPath) -> str:
    normalized = library_path.as_posix().replace("\\", "/").strip("/")
    return normalized or library_path.as_posix()


def _lookup_entry(data: dict[str, object], library_path: PurePosixPath) -> object | None:
    key = _path_key(library_path)
    raw = data.get(key)
    if raw is not None:
        return raw
    if key.startswith("/"):
        return data.get(key.lstrip("/"))
    return data.get(f"/{key}")


def _parse_saved_entry(raw: object) -> SavedTrackSelection | None:
    if not isinstance(raw, dict):
        return None
    subtitle_off = bool(raw.get("subtitle_off", False))
    subtitle_label = raw.get("subtitle_label")
    subtitle_path = raw.get("subtitle_path")
    aid = raw.get("aid")
    sid = raw.get("sid")
    parsed_aid: int | None
    parsed_sid: int | None
    try:
        parsed_aid = int(aid) if aid is not None else None
    except (TypeError, ValueError):
        parsed_aid = None
    try:
        parsed_sid = int(sid) if sid is not None else None
    except (TypeError, ValueError):
        parsed_sid = None
    parsed_path: PurePosixPath | None = None
    if isinstance(subtitle_path, str) and subtitle_path.strip():
        parsed_path = PurePosixPath(subtitle_path)
    parsed_label = subtitle_label if isinstance(subtitle_label, str) and subtitle_label else None
    return SavedTrackSelection(
        aid=parsed_aid,
        sid=parsed_sid,
        subtitle_off=subtitle_off,
        subtitle_label=parsed_label,
        subtitle_path=parsed_path,
    )


def load_track_selection(
    library_path: PurePosixPath,
    *,
    path: Path | None = None,
) -> SavedTrackSelection | None:
    selection_path = path or track_selection_path()
    if not selection_path.is_file():
        return None
    try:
        with selection_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read track selection from %s: %s", selection_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    return _parse_saved_entry(_lookup_entry(data, library_path))


def save_track_selection(
    library_path: PurePosixPath,
    selection: SavedTrackSelection,
    *,
    path: Path | None = None,
) -> None:
    selection_path = path or track_selection_path()
    key = _path_key(library_path)
    try:
        if selection_path.is_file():
            with selection_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                data = {}
        else:
            data = {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read track selection from %s: %s", selection_path, exc)
        data = {}

    data[key] = {
        "aid": selection.aid,
        "sid": selection.sid,
        "subtitle_off": selection.subtitle_off,
        "subtitle_label": selection.subtitle_label,
        "subtitle_path": (
            selection.subtitle_path.as_posix() if selection.subtitle_path is not None else None
        ),
    }

    try:
        selection_path.parent.mkdir(parents=True, exist_ok=True)
        with selection_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        logger.warning("Could not save track selection to %s: %s", selection_path, exc)
