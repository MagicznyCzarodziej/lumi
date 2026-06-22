from __future__ import annotations

from pathlib import PurePosixPath
from unittest.mock import MagicMock, patch

from lumi.infrastructure.mock.mock_file_repository import MockFileRepository
from lumi.infrastructure.subtitles.hash_reader import read_napi_hash_bytes


def test_read_napi_hash_bytes_encodes_special_characters_in_stream_uri() -> None:
    repo = MockFileRepository()
    stream_uri = "http://127.0.0.1:12345/stream/token/Back to the Future.mkv"
    payload = b"x" * 1024

    with patch(
        "lumi.infrastructure.subtitles.hash_reader.request.urlopen",
    ) as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = payload
        data = read_napi_hash_bytes(
            video_path=PurePosixPath("/Movies/Foo.mkv"),
            video_reader=repo,
            stream_uri=stream_uri,
        )

    called_uri = urlopen.call_args[0][0].full_url
    assert "Back%20to%20the%20Future.mkv" in called_uri
    assert data == payload


def test_read_napi_hash_bytes_falls_back_to_resolved_smb_path() -> None:
    repo = MockFileRepository()
    hint = PurePosixPath("/Movies/Foo.mkv")
    resolved = PurePosixPath("/media/Movies/Foo.mkv")
    repo.seed_file(resolved, b"from-smb")

    with patch("lumi.infrastructure.subtitles.hash_reader._read_http_range", return_value=None):
        data = read_napi_hash_bytes(
            video_path=hint,
            video_reader=repo,
            resolved_video_path=resolved,
            stream_uri="http://127.0.0.1:1/stream/token/movie.mkv",
        )

    assert data == b"from-smb"


def test_read_napi_hash_bytes_uses_resolver_when_needed() -> None:
    repo = MockFileRepository()
    hint = PurePosixPath("/Movies/Foo.mkv")
    resolved = PurePosixPath("/media/Movies/Foo.mkv")
    repo.seed_file(resolved, b"resolved")

    resolver = MagicMock()
    resolver.resolve_path.return_value = resolved

    with patch("lumi.infrastructure.subtitles.hash_reader._read_http_range", return_value=None):
        data = read_napi_hash_bytes(
            video_path=hint,
            video_reader=repo,
            playback_uri_resolver=resolver,
        )

    resolver.resolve_path.assert_called_once_with(hint)
    assert data == b"resolved"
