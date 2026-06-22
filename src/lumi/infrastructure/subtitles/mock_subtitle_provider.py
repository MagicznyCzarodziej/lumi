"""Mock subtitle provider for development."""

from __future__ import annotations

from lumi.domain.subtitles.provider import SubtitleDownloadError


class MockSubtitleDownloadProvider:
    def download_by_hash(self, movie_hash: str, *, language: str) -> bytes:
        if not movie_hash:
            raise SubtitleDownloadError("Missing movie hash")
        body = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            f"Mock NapiProjekt subtitle ({language})\n"
        )
        return body.encode("utf-8")
