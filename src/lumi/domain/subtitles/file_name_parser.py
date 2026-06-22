"""Subtitle file name helpers."""

from __future__ import annotations


def _normalize_extension(extension: str) -> str:
    return extension.lower().lstrip(".")


def _normalize_extensions(subtitle_extensions: set[str]) -> set[str]:
    return {_normalize_extension(ext) for ext in subtitle_extensions}


def is_subtitle_file(file_name: str, subtitle_extensions: set[str]) -> bool:
    extension = _normalize_extension(file_name.rsplit(".", 1)[-1] if "." in file_name else "")
    return extension in _normalize_extensions(subtitle_extensions)
