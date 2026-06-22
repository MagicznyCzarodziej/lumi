"""On-disk NapiProjekt subtitle cache."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath


class DiskSubtitleCache:
    """Caches subtitle bytes keyed by SHA-256 of the library video path."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def _ensure_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def cache_key(self, video_path: PurePosixPath) -> str:
        return hashlib.sha256(video_path.as_posix().encode("utf-8")).hexdigest()

    def cache_file(self, video_path: PurePosixPath) -> Path:
        return self._cache_dir / f"{self.cache_key(video_path)}.srt"

    def contains(self, video_path: PurePosixPath) -> bool:
        return self.cache_file(video_path).is_file()

    def local_path(self, video_path: PurePosixPath) -> Path | None:
        path = self.cache_file(video_path)
        return path if path.is_file() else None

    def read(self, video_path: PurePosixPath) -> bytes | None:
        path = self.cache_file(video_path)
        if not path.is_file():
            return None
        return path.read_bytes()

    def write(self, video_path: PurePosixPath, data: bytes) -> Path:
        self._ensure_dir()
        path = self.cache_file(video_path)
        path.write_bytes(data)
        return path

    def delete(self, video_path: PurePosixPath) -> None:
        path = self.cache_file(video_path)
        if path.is_file():
            path.unlink()
