"""Persisted video aspect ratio keyed by library path."""

from __future__ import annotations

import json
import logging
from pathlib import Path, PurePosixPath

from lumi.domain.video_aspect import VideoAspectMode, parse_video_aspect_mode
from lumi.infrastructure.paths import video_aspect_path

logger = logging.getLogger(__name__)


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


def load_video_aspect(
    library_path: PurePosixPath,
    *,
    path: Path | None = None,
) -> VideoAspectMode | None:
    aspect_file = path or video_aspect_path()
    if not aspect_file.is_file():
        return None
    try:
        with aspect_file.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read video aspect from %s: %s", aspect_file, exc)
        return None
    if not isinstance(data, dict):
        return None
    raw = _lookup_entry(data, library_path)
    if isinstance(raw, str):
        return parse_video_aspect_mode(raw)
    if isinstance(raw, dict):
        return parse_video_aspect_mode(raw.get("mode"))
    return None


def save_video_aspect(
    library_path: PurePosixPath,
    mode: VideoAspectMode,
    *,
    path: Path | None = None,
) -> None:
    aspect_file = path or video_aspect_path()
    key = _path_key(library_path)
    try:
        if aspect_file.is_file():
            with aspect_file.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                data = {}
        else:
            data = {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read video aspect from %s: %s", aspect_file, exc)
        data = {}

    data[key] = mode.value

    try:
        aspect_file.parent.mkdir(parents=True, exist_ok=True)
        with aspect_file.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        logger.warning("Could not save video aspect to %s: %s", aspect_file, exc)
