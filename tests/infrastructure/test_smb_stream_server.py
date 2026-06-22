"""SMB HTTP stream server tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath
from unittest.mock import MagicMock, patch

import pytest

from lumi.infrastructure.smb.smb_playback_uri import SmbPlaybackUriResolver
from lumi.infrastructure.smb.smb_stream_server import SmbHttpStreamServer, parse_byte_range


def test_parse_byte_range_open_ended() -> None:
    assert parse_byte_range("bytes=0-", 1000) == (0, 999)


def test_parse_byte_range_suffix() -> None:
    assert parse_byte_range("bytes=-500", 1000) == (500, 999)


def test_parse_byte_range_closed() -> None:
    assert parse_byte_range("bytes=10-99", 1000) == (10, 99)


def test_playback_uri_uses_localhost_stream() -> None:
    repo = MagicMock()
    repo.file_size.return_value = 12345
    repo.read_file_range.return_value = b"hello"

    server = SmbHttpStreamServer(repo)
    resolver = SmbPlaybackUriResolver(repo, server, MOCK_LIBRARY_ROOT, {"mp4"})
    try:
        with patch(
            "lumi.infrastructure.smb.smb_playback_uri.resolve_playback_file",
            return_value=MOCK_LIBRARY_ROOT / "Alien/Alien.mkv",
        ):
            uri = resolver.playback_uri(MOCK_LIBRARY_ROOT / "Alien/Alien.mkv")
        assert uri.startswith("http://127.0.0.1:")
        assert "/stream/" in uri
        assert uri.endswith("/Alien.mkv")
    finally:
        server.shutdown()


def test_resolve_stream_uri_encodes_filename() -> None:
    repo = MagicMock()
    repo.file_size.return_value = 12345
    server = SmbHttpStreamServer(repo)
    try:
        uri = server.resolve_stream_uri(PurePosixPath("/Movies/Back to the Future.mkv"))
        assert "Back%20to%20the%20Future.mkv" in uri
    finally:
        server.shutdown()


def test_playback_uri_missing_file_raises() -> None:
    repo = MagicMock()
    server = SmbHttpStreamServer(repo)
    resolver = SmbPlaybackUriResolver(repo, server, MOCK_LIBRARY_ROOT, {"mp4"})
    try:
        with patch(
            "lumi.infrastructure.smb.smb_playback_uri.resolve_playback_file",
            side_effect=FileNotFoundError("SMB file not found: missing"),
        ):
            with pytest.raises(FileNotFoundError):
                resolver.playback_uri(PurePosixPath("missing.mkv"))
    finally:
        server.shutdown()
