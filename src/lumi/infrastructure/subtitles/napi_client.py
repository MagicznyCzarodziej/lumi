"""NapiProjekt HTTP client."""

from __future__ import annotations

import io
import logging
from urllib import request

import py7zr
from py7zr.io import BytesIOFactory

from lumi.domain.subtitles.napi_language import normalize_napi_language
from lumi.domain.subtitles.provider import SubtitleDownloadError
from lumi.infrastructure.subtitles.napi_encoding import decode_subtitle_bytes

logger = logging.getLogger(__name__)

NAPI_ARCHIVE_PASSWORD = "iBlm8NTigvru0Jr0"
NAPI_BASE_URL = "http://napiprojekt.pl/unit_napisy/dl.php"


def _cipher(movie_hash: str) -> str:
    idx = [0xE, 0x3, 0x6, 0x8, 0x2]
    mul = [2, 2, 5, 4, 3]
    add = [0, 0xD, 0x10, 0xB, 0x5]
    parts: list[str] = []
    for i in range(len(idx)):
        position = add[i] + int(movie_hash[idx[i]], 16)
        value = int(movie_hash[position : position + 2], 16)
        parts.append(f"{value * mul[i]:x}"[-1])
    return "".join(parts)


def _build_url(movie_hash: str, language: str) -> str:
    import os

    lang = normalize_napi_language(language)
    return (
        f"{NAPI_BASE_URL}?l={lang}&f={movie_hash}&t={_cipher(movie_hash)}"
        f"&v=other&kolejka=false&nick=&pass=&napios={os.name}"
    )


def _unpack_7z(content: bytes) -> bytes:
    if content.startswith(b"NPc"):
        raise SubtitleDownloadError("No subtitles found")
    try:
        factory = BytesIOFactory(limit=10 * 1024 * 1024)
        with py7zr.SevenZipFile(
            io.BytesIO(content),
            mode="r",
            password=NAPI_ARCHIVE_PASSWORD,
        ) as archive:
            names = archive.getnames()
            if not names:
                raise SubtitleDownloadError("Empty subtitle archive")
            archive.extract(targets=[names[0]], factory=factory)
            payload = factory.get(names[0])
            return bytes(payload.read())
    except py7zr.Bad7zFile as exc:
        logger.warning(
            "NapiProjekt response was not a subtitle archive (first bytes: %r)",
            content[:16],
        )
        raise SubtitleDownloadError("No subtitles found") from exc


class NapiProjektClient:
    def download_by_hash(self, movie_hash: str, *, language: str) -> bytes:
        url = _build_url(movie_hash, language)
        try:
            with request.urlopen(url, timeout=30) as response:
                raw = response.read()
        except OSError as exc:
            logger.warning("NapiProjekt request failed: %s", exc)
            raise SubtitleDownloadError("Network error while downloading subtitles") from exc

        if not raw:
            raise SubtitleDownloadError("No subtitles found")

        unpacked = _unpack_7z(raw)
        text = decode_subtitle_bytes(unpacked)
        return text.encode("utf-8")
