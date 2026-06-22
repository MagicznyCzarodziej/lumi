"""Sidecar subtitle path beside a video file."""

from __future__ import annotations

from pathlib import PurePosixPath


def subtitle_sidecar_path(video_path: PurePosixPath, *, extension: str = ".srt") -> PurePosixPath:
    ext = extension if extension.startswith(".") else f".{extension}"
    stem = PurePosixPath(video_path.name).stem
    parent = video_path.parent if video_path.name else video_path
    return parent / f"{stem}{ext}"
