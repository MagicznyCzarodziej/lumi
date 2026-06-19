"""Mixed media grouping classification strategy."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.ids import entry_id_from_path
from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.library.building.file_name_parser import (
    extract_season_number_from_episode,
    get_ordinal_number_from_name,
    is_video_file,
    parse_episode_details,
    parse_name,
    resolve_season_ordinal_number,
)
from lumi.domain.library.entry_ordering import episode_sort_key, episodes_group_sort_key
from lumi.domain.library.building.strategies.classifier import (
    ChildType,
    ChildTypeKind,
    ClassificationContext,
    MediaClassifierStrategy,
)
from lumi.domain.library.models import (
    EpisodesGroup,
    Episode,
    LibraryEntry,
    MediaGrouping,
    MediaGroupingEntry,
    MediaGroupingFilm,
    Name,
    VideoFile,
)


class MediaGroupingStrategy:
    def is_applicable(self, context: ClassificationContext) -> bool:
        if context.video_files or not context.subdirectories:
            return False

        child_types = [_classify_subdirectory(context, subdir) for subdir in context.subdirectories]
        contains_films = any(child.kind is ChildTypeKind.FILM for child in child_types)
        contains_seasons = any(child.kind is ChildTypeKind.SEASON for child in child_types)
        return contains_films and contains_seasons

    def classify(self, context: ClassificationContext) -> LibraryEntry:
        poster_path = context.poster_provider.find_poster_image_with_fallback(
            directory_absolute_path=context.directory.absolute_path,
        )
        child_types = [_classify_subdirectory(context, subdir) for subdir in context.subdirectories]
        entries: list[MediaGroupingEntry] = sorted(
            (
                entry
                for index, child in enumerate(child_types)
                if (entry := _child_to_entry(context, child, index + 1, poster_path)) is not None
            ),
            key=_media_grouping_sort_key,
        )
        return MediaGrouping(
            id=entry_id_from_path(context.directory.absolute_path),
            name=parse_name(context.directory.name),
            root_relative_path=context.directory.absolute_path,
            root_relative_poster_path=poster_path,
            tags=frozenset(context.lumi_directory_config.tags),
            franchise=context.lumi_directory_config.franchise,
            entries=entries,
        )


def _media_grouping_sort_key(entry: MediaGroupingEntry) -> tuple[int, int | None, int | None, str | None]:
    if isinstance(entry, EpisodesGroup):
        return (0, entry.ordinal_number, None, None)
    return (1, None, entry.ordinal_number, entry.name.name)


def _child_to_entry(
    context: ClassificationContext,
    child: ChildType,
    fallback_number: int,
    main_poster_path: PurePosixPath,
) -> MediaGroupingEntry | None:
    if child.kind is ChildTypeKind.FILM and child.directory is not None:
        return _process_film(context, child.directory, main_poster_path)
    if child.kind is ChildTypeKind.SEASON and child.directory is not None:
        return _process_season(context, child.directory, fallback_number, main_poster_path)
    return None


def _process_film(
    context: ClassificationContext,
    film_dir: DirectoryEntry,
    main_poster_path: PurePosixPath,
) -> MediaGroupingFilm:
    video_files = sorted(
        (
            VideoFile(name=Name(entry.name), absolute_path=entry.absolute_path)
            for entry in context.file_lister.list_files_and_directories(film_dir.absolute_path)
            if entry.is_file and is_video_file(entry.name, context.video_extensions)
        ),
        key=lambda vf: vf.name.name,
    )
    poster_path = (
        context.poster_provider.find_poster_image(directory_absolute_path=film_dir.absolute_path)
        or main_poster_path
    )
    return MediaGroupingFilm(
        id=entry_id_from_path(film_dir.absolute_path),
        name=parse_name(film_dir.name),
        root_relative_path=film_dir.absolute_path,
        root_relative_poster_path=poster_path,
        ordinal_number=get_ordinal_number_from_name(film_dir.name) or 0,
        video_files=video_files,
    )


def _process_season(
    context: ClassificationContext,
    season_dir: DirectoryEntry,
    fallback_number: int,
    main_poster_path: PurePosixPath,
) -> EpisodesGroup | None:
    episode_files = [
        entry
        for entry in context.file_lister.list_files_and_directories(season_dir.absolute_path)
        if entry.is_file and is_video_file(entry.name, context.video_extensions)
    ]
    if not episode_files:
        return None

    episodes = sorted(
        (_parse_episode(entry, context) for entry in episode_files),
        key=episode_sort_key,
    )
    poster_path = (
        context.poster_provider.find_poster_image(directory_absolute_path=season_dir.absolute_path)
        or main_poster_path
    )
    return EpisodesGroup(
        id=entry_id_from_path(season_dir.absolute_path),
        name=Name(season_dir.name),
        root_relative_path=season_dir.absolute_path,
        root_relative_poster_path=poster_path,
        ordinal_number=resolve_season_ordinal_number(
            season_dir.name,
            episode_file_names=tuple(entry.name for entry in episode_files),
            fallback_number=fallback_number,
        ),
        episodes=episodes,
    )


def _parse_episode(file: DirectoryEntry, context: ClassificationContext) -> Episode:
    details = parse_episode_details(
        file_name=file.name,
        video_extensions=context.video_extensions,
        series_name=context.directory.name,
    )
    return Episode(
        id=entry_id_from_path(file.absolute_path),
        name=Name(details.title),
        root_relative_path=file.absolute_path,
        ordinal_number=details.number,
    )


def _classify_subdirectory(context: ClassificationContext, subdirectory: DirectoryEntry) -> ChildType:
    files = [
        entry
        for entry in context.file_lister.list_files_and_directories(subdirectory.absolute_path)
        if entry.is_file and is_video_file(entry.name, context.video_extensions)
    ]
    is_season_like = len(files) > 1 or any(
        extract_season_number_from_episode(entry.name) is not None for entry in files
    )
    is_film_like = len(files) == 1 and not is_season_like

    if is_season_like:
        return ChildType.season(subdirectory)
    if is_film_like:
        return ChildType.film(subdirectory)
    return ChildType.empty()
