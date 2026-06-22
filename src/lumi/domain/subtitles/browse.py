"""Build folder browser rows for manual subtitle selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pathlib import PurePosixPath

from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.domain.filesystem.path_candidates import library_path_candidates
from lumi.domain.subtitles.file_name_parser import is_subtitle_file


class BrowseEntryKind(str, Enum):
    PARENT = "parent"
    DIRECTORY = "directory"
    SUBTITLE = "subtitle"


@dataclass(frozen=True)
class BrowseRow:
    label: str
    path: PurePosixPath
    kind: BrowseEntryKind


def share_path(path: PurePosixPath) -> PurePosixPath:
    text = path.as_posix().replace("\\", "/").strip("/")
    if not text:
        return PurePosixPath("/")
    return PurePosixPath(f"/{text}")


def parent_directory(directory: PurePosixPath) -> PurePosixPath | None:
    normalized = share_path(directory)
    if not normalized.name:
        return None
    parent = normalized.parent
    if parent == normalized:
        return None
    return parent


def _list_directory(
    files_lister: FilesLister,
    directory: PurePosixPath,
    *,
    library_root: PurePosixPath | None = None,
) -> tuple[list[DirectoryEntry], PurePosixPath]:
    """List a share directory, using path variants only when the direct path is empty."""
    normalized = share_path(directory)
    entries = files_lister.list_files_and_directories(normalized)
    if entries:
        return entries, normalized

    if library_root is None or not str(library_root).strip("/"):
        return entries, normalized

    root = share_path(library_root)
    for candidate in library_path_candidates(normalized, root):
        if candidate == normalized:
            continue
        entries = files_lister.list_files_and_directories(candidate)
        if entries:
            return entries, share_path(candidate)

    return entries, normalized


def build_browse_rows(
    files_lister: FilesLister,
    directory: PurePosixPath,
    subtitle_extensions: set[str],
    *,
    library_root: PurePosixPath | None = None,
) -> tuple[list[BrowseRow], PurePosixPath]:
    """Return navigable rows for a share directory and the resolved listing path."""
    entries, resolved_directory = _list_directory(
        files_lister,
        directory,
        library_root=library_root,
    )
    rows: list[BrowseRow] = []

    parent = parent_directory(resolved_directory)
    if parent is not None:
        rows.append(BrowseRow(label="..", path=parent, kind=BrowseEntryKind.PARENT))

    directories = sorted(
        (entry for entry in entries if entry.is_directory),
        key=lambda entry: entry.name.lower(),
    )
    subtitles = sorted(
        (
            entry
            for entry in entries
            if entry.is_file and is_subtitle_file(entry.name, subtitle_extensions)
        ),
        key=lambda entry: entry.name.lower(),
    )

    for entry in directories:
        rows.append(
            BrowseRow(
                label=f"{entry.name}/",
                path=share_path(entry.absolute_path),
                kind=BrowseEntryKind.DIRECTORY,
            )
        )
    for entry in subtitles:
        rows.append(
            BrowseRow(
                label=entry.name,
                path=share_path(entry.absolute_path),
                kind=BrowseEntryKind.SUBTITLE,
            )
        )

    return rows, resolved_directory
