"""Subtitle download provider protocol."""

from __future__ import annotations

from typing import Protocol


class SubtitleDownloadError(Exception):
    """Subtitle could not be downloaded."""


class SubtitleDownloadProvider(Protocol):
    def download_by_hash(self, movie_hash: str, *, language: str) -> bytes:
        """Return UTF-8 SRT bytes for the given NapiProjekt hash."""
        ...
