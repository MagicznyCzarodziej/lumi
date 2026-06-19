"""Poster image discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import PurePosixPath

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import FilesLister


class PosterImageNotFound(RuntimeError):
    pass


DEFAULT_POSTER_PATH = PurePosixPath("defaultPoster.jpg")


def is_placeholder_poster_path(path: PurePosixPath) -> bool:
    return path.name == DEFAULT_POSTER_PATH.name or path.as_posix() == DEFAULT_POSTER_PATH.as_posix()


class ImageFilePosterProvider:
    def __init__(
        self,
        file_repository: FileRepository,
        files_lister: FilesLister,
        poster_file_name: str,
        supported_file_extensions: set[str],
    ) -> None:
        self._file_repository = file_repository
        self._files_lister = files_lister
        self._poster_file_name = poster_file_name
        self._supported_file_extensions = {_normalize_extension(ext) for ext in supported_file_extensions}

    def find_poster_image(self, directory_absolute_path: PurePosixPath) -> PurePosixPath | None:
        for extension in self._supported_file_extensions:
            poster = self._find_poster_file_for_extension(directory_absolute_path, extension)
            if poster is not None:
                return poster
        return None

    def find_poster_image_with_fallback(self, directory_absolute_path: PurePosixPath) -> PurePosixPath:
        return self.find_poster_image(directory_absolute_path) or PurePosixPath("defaultPoster.jpg")

    def copy_poster_image_to(
        self,
        poster_image_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], object],
    ) -> bool:
        result = self._file_repository.use_read_file_stream(poster_image_path, block)
        return result is not None

    def get_poster_image(self, poster_image_path: PurePosixPath) -> bytes:
        def read_all(stream: Iterator[bytes]) -> bytes:
            return b"".join(stream)

        data = self._file_repository.use_read_file_stream(poster_image_path, read_all)
        if data is None:
            raise PosterImageNotFound(poster_image_path)
        return data

    def fetch_poster_bytes(self, directory_or_file_path: PurePosixPath) -> bytes:
        """Load poster bytes for a library directory path or direct image file path."""
        if is_placeholder_poster_path(directory_or_file_path):
            raise PosterImageNotFound(directory_or_file_path)

        if _has_image_extension(directory_or_file_path, self._supported_file_extensions):
            return self.get_poster_image(directory_or_file_path)

        poster_file = self.find_poster_image(directory_or_file_path)
        if poster_file is None:
            raise PosterImageNotFound(directory_or_file_path)
        return self.get_poster_image(poster_file)

    def _find_poster_file_for_extension(
        self,
        directory_absolute_path: PurePosixPath,
        extension: str,
    ) -> PurePosixPath | None:
        poster_image_path = directory_absolute_path / f"{self._poster_file_name}.{extension}"
        files_in_directory = self._files_lister.list_files_and_directories(directory_absolute_path)
        if any(entry.absolute_path == poster_image_path for entry in files_in_directory):
            return poster_image_path
        return None


def _normalize_extension(extension: str) -> str:
    return extension.lower().lstrip(".")


def _has_image_extension(path: PurePosixPath, supported_extensions: set[str]) -> bool:
    suffix = path.suffix.lower().lstrip(".")
    return bool(suffix) and suffix in supported_extensions
