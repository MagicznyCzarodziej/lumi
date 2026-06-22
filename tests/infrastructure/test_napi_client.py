from __future__ import annotations

from pathlib import PurePosixPath
from unittest.mock import patch

import pytest

from lumi.domain.subtitles.provider import SubtitleDownloadError
from lumi.infrastructure.subtitles.mock_subtitle_provider import MockSubtitleDownloadProvider
from lumi.infrastructure.subtitles.napi_client import NapiProjektClient
from lumi.infrastructure.subtitles.napi_encoding import decode_subtitle_bytes


def test_mock_subtitle_provider_returns_utf8_srt() -> None:
    data = MockSubtitleDownloadProvider().download_by_hash("abc123", language="PL")
    assert "Mock NapiProjekt subtitle (PL)" in data.decode("utf-8")


def test_decode_subtitle_bytes_prefers_utf8() -> None:
    text = "ąćęłńóśżź"
    assert decode_subtitle_bytes(text.encode("utf-8")) == text


def test_napi_client_unpacks_passworded_7z_archive() -> None:
    import io

    import py7zr

    buffer = io.BytesIO()
    with py7zr.SevenZipFile(buffer, "w", password="iBlm8NTigvru0Jr0") as archive:
        archive.writestr("1\n00:00:01,000 --> 00:00:02,000\nHello\n", "sub.srt")

    from lumi.infrastructure.subtitles.napi_client import _unpack_7z

    assert b"Hello" in _unpack_7z(buffer.getvalue())


def test_napi_client_raises_on_not_found_response() -> None:
    client = NapiProjektClient()
    movie_hash = "a" * 32
    with patch("lumi.infrastructure.subtitles.napi_client.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = b"NPc0"
        with pytest.raises(SubtitleDownloadError, match="No subtitles found"):
            client.download_by_hash(movie_hash, language="ENG")


def test_napi_client_raises_when_archive_empty() -> None:
    client = NapiProjektClient()
    movie_hash = "a" * 32
    with patch("lumi.infrastructure.subtitles.napi_client.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = b"not-a-7z"
        with pytest.raises(SubtitleDownloadError, match="No subtitles found"):
            client.download_by_hash(movie_hash, language="ENG")
