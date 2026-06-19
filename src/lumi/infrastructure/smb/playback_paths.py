"""SMB playback path normalization and file resolution."""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from lumi.domain.library.building.file_name_parser import is_video_file
from lumi.domain.filesystem.files_lister import DirectoryEntry
from lumi.infrastructure.smb.connection import share_relative_path
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository

logger = logging.getLogger(__name__)


def _normalize_posix(path: PurePosixPath) -> str:
    return path.as_posix().replace("\\", "/").strip("/")


def playback_path_candidates(absolute_path: PurePosixPath, library_root: PurePosixPath) -> list[PurePosixPath]:
    """Return path variants to try on the SMB share (with/without library root prefix)."""
    text = _normalize_posix(absolute_path)
    root = _normalize_posix(library_root)

    variants: list[str] = []
    if text:
        variants.append(text)
    if root:
        if text.startswith(f"{root}/"):
            variants.append(text[len(root) + 1 :])
        elif text != root:
            variants.append(f"{root}/{text}")

    seen: set[str] = set()
    candidates: list[PurePosixPath] = []
    for variant in variants:
        if not variant or variant in seen:
            continue
        seen.add(variant)
        candidates.append(PurePosixPath(f"/{variant}"))
    return candidates or [absolute_path]


def directory_path_candidates(path: PurePosixPath, library_root: PurePosixPath) -> list[PurePosixPath]:
    """Directory variants for re-scanning when a cached file path cannot be opened."""
    parent = path.parent if path.name else path
    return playback_path_candidates(parent, library_root)


def _pick_video_file(videos: list[DirectoryEntry], preferred_name: str) -> DirectoryEntry:
    if len(videos) == 1:
        return videos[0]
    preferred = preferred_name.lower()
    for entry in videos:
        if entry.name.lower() == preferred:
            return entry
    return sorted(videos, key=lambda entry: entry.name)[0]


def resolve_playback_file(
    smb_file_repository: SmbFileRepository,
    hint_path: PurePosixPath,
    library_root: PurePosixPath,
    video_extensions: set[str],
) -> PurePosixPath:
    """Resolve a library path to an SMB video file readable right now."""
    for candidate in playback_path_candidates(hint_path, library_root):
        size = smb_file_repository.file_size(candidate)
        if size is not None:
            logger.info(
                "Resolved playback file %s (%d bytes on share)",
                share_relative_path(candidate),
                size,
            )
            return candidate

    for directory in directory_path_candidates(hint_path, library_root):
        entries = smb_file_repository.list_files_and_directories(directory)
        videos = [
            entry
            for entry in entries
            if entry.is_file and is_video_file(entry.name, video_extensions)
        ]
        if not videos:
            continue
        chosen = _pick_video_file(videos, hint_path.name)
        size = smb_file_repository.file_size(chosen.absolute_path)
        if size is not None:
            logger.info(
                "Resolved playback file via directory scan %s -> %s (%d bytes)",
                share_relative_path(directory),
                share_relative_path(chosen.absolute_path),
                size,
            )
            return chosen.absolute_path

    tried = [share_relative_path(path) for path in playback_path_candidates(hint_path, library_root)]
    logger.error("Could not resolve SMB playback file for %s (tried: %s)", hint_path, ", ".join(tried))
    raise FileNotFoundError(f"SMB file not found: {hint_path}")
