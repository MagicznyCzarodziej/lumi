"""Persist NapiProjekt save-to-NAS state."""

from __future__ import annotations

import json
import logging
from pathlib import Path, PurePosixPath

from lumi.infrastructure.paths import napi_saved_state_path

logger = logging.getLogger(__name__)


class JsonNapiSavedStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or napi_saved_state_path()

    def _path_key(self, video_path: PurePosixPath) -> str:
        return video_path.as_posix()

    def _load(self) -> dict[str, bool]:
        if not self._path.is_file():
            return {}
        try:
            with self._path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read NapiProjekt saved state from %s: %s", self._path, exc)
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): bool(value) for key, value in data.items() if value}

    def _save(self, data: dict[str, bool]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
        except OSError as exc:
            logger.warning("Could not save NapiProjekt saved state to %s: %s", self._path, exc)

    def is_saved_to_nas(self, video_path: PurePosixPath) -> bool:
        return self._load().get(self._path_key(video_path), False)

    def mark_saved_to_nas(self, video_path: PurePosixPath) -> None:
        data = self._load()
        data[self._path_key(video_path)] = True
        self._save(data)

    def clear(self, video_path: PurePosixPath) -> None:
        data = self._load()
        key = self._path_key(video_path)
        if key in data:
            del data[key]
            self._save(data)
