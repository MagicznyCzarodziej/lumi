"""Library path variants for SMB shares (with/without configured root prefix)."""

from __future__ import annotations

from pathlib import PurePosixPath


def _normalize_posix(path: PurePosixPath) -> str:
    return path.as_posix().replace("\\", "/").strip("/")


def library_path_candidates(absolute_path: PurePosixPath, library_root: PurePosixPath) -> list[PurePosixPath]:
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
    """Directory variants for listing when a cached path cannot be opened."""
    parent = path.parent if path.name else path
    return library_path_candidates(parent, library_root)
