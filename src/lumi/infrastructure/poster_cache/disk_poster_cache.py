"""On-disk poster image cache."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath


class DiskPosterCache:
    """Caches poster image bytes keyed by SHA-256 of the share-relative path."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = Path(cache_dir)

    def _ensure_dir(self) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def cache_key(self, poster_path: PurePosixPath) -> str:
        return hashlib.sha256(poster_path.as_posix().encode("utf-8")).hexdigest()

    def cache_file(self, poster_path: PurePosixPath) -> Path:
        return self._cache_dir / self.cache_key(poster_path)

    def contains(self, poster_path: PurePosixPath) -> bool:
        return self.cache_file(poster_path).is_file()

    def read(self, poster_path: PurePosixPath) -> bytes | None:
        path = self.cache_file(poster_path)
        if not path.is_file():
            return None
        return path.read_bytes()

    def write(self, poster_path: PurePosixPath, data: bytes) -> Path:
        self._ensure_dir()
        path = self.cache_file(poster_path)
        path.write_bytes(data)
        return path
