"""Read the first 10 MB of a playing file for NapiProjekt hashing."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import PurePosixPath
from urllib import request
from urllib.parse import quote, urlsplit, urlunsplit

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.napi_hash import NAPI_HASH_BYTES
from lumi.domain.subtitles.provider import SubtitleDownloadError

logger = logging.getLogger(__name__)


def _encode_request_uri(uri: str) -> str:
    parts = urlsplit(uri)
    safe_path = quote(parts.path, safe="/")
    return urlunsplit((parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment))


def _read_http_range(uri: str, offset: int, length: int) -> bytes | None:
    end = offset + length - 1
    safe_uri = _encode_request_uri(uri)
    req = request.Request(safe_uri, headers={"Range": f"bytes={offset}-{end}"})
    try:
        with request.urlopen(req, timeout=60) as response:
            data = response.read()
    except OSError as exc:
        logger.warning("Could not read playback stream for hash (%s): %s", safe_uri, exc)
        return None
    return data if data else None


def _read_prefix_from_stream(
    file_repository: FileRepository,
    path: PurePosixPath,
) -> bytes | None:
    def collect(chunks: Iterator[bytes]) -> bytes:
        buffer = bytearray()
        for chunk in chunks:
            buffer.extend(chunk)
            if len(buffer) >= NAPI_HASH_BYTES:
                return bytes(buffer[:NAPI_HASH_BYTES])
        return bytes(buffer)

    return file_repository.use_read_file_stream(path, collect)


def _is_local_stream_uri(uri: str) -> bool:
    return uri.startswith("http://127.0.0.1:") or uri.startswith("http://127.0.0.1/")


def read_napi_hash_bytes(
    *,
    video_path: PurePosixPath,
    video_reader: VideoRangeReader,
    playback_uri_resolver: PlaybackUriResolver | None = None,
    stream_uri: str | None = None,
    resolved_video_path: PurePosixPath | None = None,
    file_repository: FileRepository | None = None,
) -> bytes:
    if stream_uri and _is_local_stream_uri(stream_uri):
        data = _read_http_range(stream_uri, 0, NAPI_HASH_BYTES)
        if data:
            return data

    paths: list[PurePosixPath] = []
    if resolved_video_path is not None:
        paths.append(resolved_video_path)
    if playback_uri_resolver is not None:
        try:
            resolved = playback_uri_resolver.resolve_path(video_path)
        except OSError:
            resolved = None
        if resolved is not None and resolved not in paths:
            paths.append(resolved)
    if video_path not in paths:
        paths.append(video_path)

    for path in paths:
        data = video_reader.read_file_range(path, 0, NAPI_HASH_BYTES)
        if data:
            return data
        if file_repository is not None:
            data = _read_prefix_from_stream(file_repository, path)
            if data:
                return data
        logger.warning("Could not read video prefix from SMB path %s", path.as_posix())

    raise SubtitleDownloadError("Could not read video for hash")
