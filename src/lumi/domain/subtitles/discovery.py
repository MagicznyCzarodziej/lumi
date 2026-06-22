"""Discover external subtitle files near a video on the library share."""

from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.domain.filesystem.path_candidates import library_path_candidates
from lumi.domain.library.building.file_name_parser import is_video_file
from lumi.domain.subtitles.file_name_parser import is_subtitle_file


def _video_stem(video_path: PurePosixPath) -> str:
    return PurePosixPath(video_path.name).stem.lower()


def _collect_from_entries(
    entries: list[DirectoryEntry],
    video_stem: str,
    subtitle_extensions: set[str],
) -> tuple[list[PurePosixPath], list[PurePosixPath]]:
    matching: list[PurePosixPath] = []
    other: list[PurePosixPath] = []
    for entry in entries:
        if not entry.is_file:
            continue
        if not is_subtitle_file(entry.name, subtitle_extensions):
            continue
        path = entry.absolute_path
        stem = PurePosixPath(entry.name).stem.lower()
        if stem == video_stem or stem.startswith(f"{video_stem}."):
            matching.append(path)
        else:
            other.append(path)
    return matching, other


def _directories_to_scan(
    video_path: PurePosixPath,
    library_root: PurePosixPath | None,
) -> list[PurePosixPath]:
    if video_path.name:
        directories = [video_path.parent]
    else:
        directories = [video_path]

    if library_root is None:
        return directories

    expanded: list[PurePosixPath] = []
    seen: set[str] = set()
    for directory in directories:
        for candidate in library_path_candidates(directory, library_root):
            key = candidate.as_posix()
            if key in seen:
                continue
            seen.add(key)
            expanded.append(candidate)
    return expanded or directories


def discover_subtitle_files(
    files_lister: FilesLister,
    video_path: PurePosixPath,
    subtitle_extensions: set[str],
    *,
    library_root: PurePosixPath | None = None,
    video_extensions: set[str] | None = None,
) -> list[PurePosixPath]:
    """Return subtitle files beside a video, trying SMB path variants when needed."""
    resolved_video = video_path
    if video_extensions and not is_video_file(video_path.name, video_extensions):
        resolved_video = _resolve_video_in_directory(
            files_lister,
            video_path,
            video_extensions,
            library_root,
        )

    video_stem = _video_stem(resolved_video)
    matching: list[PurePosixPath] = []
    other: list[PurePosixPath] = []
    seen_files: set[str] = set()

    for directory in _directories_to_scan(resolved_video, library_root):
        entries = files_lister.list_files_and_directories(directory)
        found_matching, found_other = _collect_from_entries(
            entries, video_stem, subtitle_extensions
        )
        for path in found_matching + found_other:
            key = path.as_posix()
            if key in seen_files:
                continue
            seen_files.add(key)
            if path in found_matching:
                matching.append(path)
            else:
                other.append(path)

    return sorted(matching, key=lambda path: path.name.lower()) + sorted(
        other, key=lambda path: path.name.lower()
    )


def _resolve_video_in_directory(
    files_lister: FilesLister,
    directory: PurePosixPath,
    video_extensions: set[str],
    library_root: PurePosixPath | None,
) -> PurePosixPath:
    directories = _directories_to_scan(directory, library_root)
    for scan_dir in directories:
        entries = files_lister.list_files_and_directories(scan_dir)
        videos = [entry for entry in entries if entry.is_file and is_video_file(entry.name, video_extensions)]
        if len(videos) == 1:
            return videos[0].absolute_path
        if len(videos) > 1:
            return sorted(videos, key=lambda entry: entry.name)[0].absolute_path
    return directory
