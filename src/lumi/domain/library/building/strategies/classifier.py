"""Media classifier strategy base types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import PurePosixPath
from typing import Protocol

from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.domain.library.models import LibraryEntry
from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig
from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider


class MediaClassifierStrategy(Protocol):
    def is_applicable(self, context: ClassificationContext) -> bool: ...

    def classify(self, context: ClassificationContext) -> LibraryEntry | None: ...


@dataclass(frozen=True)
class ClassificationContext:
    directory: DirectoryEntry
    subdirectories: list[DirectoryEntry]
    video_files: list[DirectoryEntry]
    file_lister: FilesLister
    poster_provider: ImageFilePosterProvider
    video_extensions: set[str]
    lumi_directory_config: LumiDirectoryConfig


class ChildTypeKind(Enum):
    SEASON = auto()
    FILM = auto()
    EMPTY = auto()


@dataclass(frozen=True)
class ChildType:
    kind: ChildTypeKind
    directory: DirectoryEntry | None = None

    @staticmethod
    def season(directory: DirectoryEntry) -> ChildType:
        return ChildType(ChildTypeKind.SEASON, directory)

    @staticmethod
    def film(directory: DirectoryEntry) -> ChildType:
        return ChildType(ChildTypeKind.FILM, directory)

    @staticmethod
    def empty() -> ChildType:
        return ChildType(ChildTypeKind.EMPTY)
