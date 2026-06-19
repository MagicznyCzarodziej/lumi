"""Film series classification strategy."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.ids import entry_id_from_path
from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.library.building.file_name_parser import (
    get_ordinal_number_from_name,
    is_video_file,
    parse_name,
)
from lumi.domain.library.building.strategies.classifier import ClassificationContext, MediaClassifierStrategy
from lumi.domain.library.models import FilmSeries, FilmSeriesFilm, LibraryEntry, Name, VideoFile
from lumi.domain.lumi_directory_config.models import LumiDirectoryConfigType


class FilmSeriesStrategy:
    def is_applicable(self, context: ClassificationContext) -> bool:
        return context.lumi_directory_config.type is LumiDirectoryConfigType.FILM_SERIES

    def classify(self, context: ClassificationContext) -> LibraryEntry:
        poster_path = context.poster_provider.find_poster_image_with_fallback(
            directory_absolute_path=context.directory.absolute_path,
        )
        films = sorted(
            (
                film
                for film_dir in context.subdirectories
                if (film := _process_film(context, film_dir, poster_path)) is not None
            ),
            key=lambda item: (item.ordinal_number, item.name.name),
        )
        return FilmSeries(
            id=entry_id_from_path(context.directory.absolute_path),
            name=parse_name(context.directory.name),
            root_relative_path=context.directory.absolute_path,
            root_relative_poster_path=poster_path,
            tags=frozenset(context.lumi_directory_config.tags),
            franchise=context.lumi_directory_config.franchise,
            films=films,
        )


def _process_film(
    context: ClassificationContext,
    film_dir: DirectoryEntry,
    main_poster_path: PurePosixPath,
) -> FilmSeriesFilm | None:
    video_files = sorted(
        (
            VideoFile(name=Name(entry.name), absolute_path=entry.absolute_path)
            for entry in context.file_lister.list_files_and_directories(film_dir.absolute_path)
            if entry.is_file and is_video_file(entry.name, context.video_extensions)
        ),
        key=lambda vf: vf.name.name,
    )
    if not video_files:
        return None

    poster_path = (
        context.poster_provider.find_poster_image(directory_absolute_path=film_dir.absolute_path)
        or main_poster_path
    )
    return FilmSeriesFilm(
        id=entry_id_from_path(film_dir.absolute_path),
        name=parse_name(film_dir.name),
        root_relative_path=film_dir.absolute_path,
        root_relative_poster_path=poster_path,
        ordinal_number=get_ordinal_number_from_name(film_dir.name) or 0,
        video_files=video_files,
    )
