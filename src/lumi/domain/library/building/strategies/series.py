"""Series classification strategy."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.ids import entry_id_from_path
from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.domain.library.building.file_name_parser import (
    is_video_file,
    parse_episode_details,
    parse_name,
    resolve_season_ordinal_number,
)
from lumi.domain.library.building.patterns import EPISODE_FILE_PATTERN
from lumi.domain.library.entry_ordering import episode_sort_key, episodes_group_sort_key
from lumi.domain.library.building.strategies.classifier import (
    ChildType,
    ChildTypeKind,
    ClassificationContext,
    MediaClassifierStrategy,
)
from lumi.domain.library.models import EpisodesGroup, Episode, LibraryEntry, Name, Series


class SeriesStrategy:
    def is_applicable(self, context: ClassificationContext) -> bool:
        if context.video_files or not context.subdirectories:
            return False

        child_types = [_classify_subdirectory(context, subdir) for subdir in context.subdirectories]
        contains_films = any(child.kind is ChildTypeKind.FILM for child in child_types)
        contains_seasons = any(child.kind is ChildTypeKind.SEASON for child in child_types)
        return contains_seasons and not contains_films

    def classify(self, context: ClassificationContext) -> LibraryEntry:
        poster_path = context.poster_provider.find_poster_image_with_fallback(
            directory_absolute_path=context.directory.absolute_path,
        )
        seasons = sorted(
            (
                season
                for index, season_dir in enumerate(context.subdirectories)
                if (
                    season := _process_season(
                        context,
                        season_dir,
                        fallback_number=index + 1,
                        main_poster_path=poster_path,
                    )
                )
                is not None
            ),
            key=episodes_group_sort_key,
        )
        return Series(
            id=entry_id_from_path(context.directory.absolute_path),
            name=parse_name(context.directory.name),
            root_relative_path=context.directory.absolute_path,
            root_relative_poster_path=poster_path,
            tags=frozenset(context.lumi_directory_config.tags),
            franchise=context.lumi_directory_config.franchise,
            seasons=seasons,
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
    if not files:
        return ChildType.empty()
    has_episode_pattern = any(EPISODE_FILE_PATTERN.matches_text_exactly(entry.name) for entry in files)
    if len(files) > 1 or has_episode_pattern:
        return ChildType.season(subdirectory)
    if len(files) == 1 and not has_episode_pattern:
        return ChildType.film(subdirectory)
    return ChildType.empty()
