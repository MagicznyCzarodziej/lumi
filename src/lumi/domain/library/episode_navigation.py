"""Previous/next episode lookup for in-player navigation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from lumi.domain.library.models import Episode, EpisodesGroup, LibraryEntry, MediaGrouping, Series


@dataclass(frozen=True)
class EpisodeNeighbors:
    previous: PurePosixPath | None
    next: PurePosixPath | None


def paths_refer_to_same_file(left: PurePosixPath, right: PurePosixPath) -> bool:
    """Match episode paths that may differ by library-root prefix."""
    left_norm = _normalize_path(left)
    right_norm = _normalize_path(right)
    if left_norm == right_norm:
        return True
    return left_norm.endswith(f"/{right_norm}") or right_norm.endswith(f"/{left_norm}")


def find_episode_neighbors(
    entries: list[LibraryEntry],
    library_path: PurePosixPath,
) -> EpisodeNeighbors:
    for entry in entries:
        if isinstance(entry, Series):
            neighbors = _neighbors_in_paths(_series_episode_paths(entry), library_path)
            if neighbors is not None:
                return neighbors
        if isinstance(entry, MediaGrouping):
            for child in entry.entries:
                if isinstance(child, EpisodesGroup):
                    paths = [episode.root_relative_path for episode in child.episodes]
                    neighbors = _neighbors_in_paths(paths, library_path)
                    if neighbors is not None:
                        return neighbors
    return EpisodeNeighbors(previous=None, next=None)


def find_episode(entries: list[LibraryEntry], library_path: PurePosixPath) -> Episode | None:
    for entry in entries:
        if isinstance(entry, Series):
            for season in entry.seasons:
                for episode in season.episodes:
                    if paths_refer_to_same_file(episode.root_relative_path, library_path):
                        return episode
        if isinstance(entry, MediaGrouping):
            for child in entry.entries:
                if isinstance(child, EpisodesGroup):
                    for episode in child.episodes:
                        if paths_refer_to_same_file(episode.root_relative_path, library_path):
                            return episode
    return None


def find_episode_display_name(entries: list[LibraryEntry], library_path: PurePosixPath) -> str | None:
    episode = find_episode(entries, library_path)
    if episode is None:
        return None
    return episode.name.name


def _normalize_path(path: PurePosixPath) -> str:
    return path.as_posix().replace("\\", "/").strip("/").casefold()


def _series_episode_paths(series: Series) -> list[PurePosixPath]:
    paths: list[PurePosixPath] = []
    for season in series.seasons:
        paths.extend(episode.root_relative_path for episode in season.episodes)
    return paths


def _neighbors_in_paths(
    paths: list[PurePosixPath],
    library_path: PurePosixPath,
) -> EpisodeNeighbors | None:
    index = next(
        (idx for idx, path in enumerate(paths) if paths_refer_to_same_file(path, library_path)),
        None,
    )
    if index is None:
        return None
    return EpisodeNeighbors(
        previous=paths[index - 1] if index > 0 else None,
        next=paths[index + 1] if index + 1 < len(paths) else None,
    )
