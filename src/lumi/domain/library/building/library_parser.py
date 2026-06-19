"""Library directory parser orchestrator."""

from __future__ import annotations

from lumi.domain.library.building.file_name_parser import is_video_file
from lumi.domain.library.building.strategies.classifier import ClassificationContext, MediaClassifierStrategy
from lumi.domain.library.building.strategies.film_series import FilmSeriesStrategy
from lumi.domain.library.building.strategies.media_grouping import MediaGroupingStrategy
from lumi.domain.library.building.strategies.series import SeriesStrategy
from lumi.domain.library.building.strategies.standalone_film import StandaloneFilmStrategy
from lumi.domain.library.models import LibraryEntry
from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.domain.lumi_directory_config.models import LumiDirectoryConfig
from lumi.domain.lumi_directory_config.provider import LumiDirectoryConfigProvider
from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider


class LibraryParser:
    def __init__(
        self,
        file_lister: FilesLister,
        poster_provider: ImageFilePosterProvider,
        video_extensions: set[str],
        lumi_directory_config_provider: LumiDirectoryConfigProvider,
    ) -> None:
        # Order only matters when is_applicable() overlaps between strategies.
        self._strategies: list[MediaClassifierStrategy] = [
            FilmSeriesStrategy(),
            StandaloneFilmStrategy(),
            MediaGroupingStrategy(),
            SeriesStrategy(),
        ]
        self._file_lister = file_lister
        self._poster_provider = poster_provider
        self._video_extensions = video_extensions
        self._lumi_directory_config_provider = lumi_directory_config_provider

    def parse_directory(self, directory: DirectoryEntry) -> LibraryEntry | None:
        children = self._file_lister.list_files_and_directories(directory.absolute_path)
        video_files = [entry for entry in children if entry.is_file and is_video_file(entry.name, self._video_extensions)]
        subdirectories = [entry for entry in children if entry.is_directory]

        lumi_directory_config = (
            self._lumi_directory_config_provider.get_lumi_directory_config_for_directory(directory.absolute_path)
            or LumiDirectoryConfig(type=None, franchise=None, tags=set())
        )

        context = ClassificationContext(
            directory=directory,
            subdirectories=subdirectories,
            video_files=video_files,
            file_lister=self._file_lister,
            poster_provider=self._poster_provider,
            video_extensions=self._video_extensions,
            lumi_directory_config=lumi_directory_config,
        )

        for strategy in self._strategies:
            if strategy.is_applicable(context):
                return strategy.classify(context)
        return None
