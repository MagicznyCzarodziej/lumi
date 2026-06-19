"""Local HTTP range server that streams SMB files to libmpv (no local copy)."""

from __future__ import annotations

import logging
import mimetypes
import re
import threading
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository

_READ_CHUNK = 1024 * 1024

logger = logging.getLogger(__name__)

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


@dataclass(frozen=True)
class _StreamEntry:
    path: PurePosixPath
    size: int
    content_type: str


def parse_byte_range(header: str | None, file_size: int) -> tuple[int, int] | None:
    if not header:
        return None
    match = _RANGE_RE.fullmatch(header.strip())
    if match is None:
        return None
    start_raw, end_raw = match.groups()
    if start_raw:
        start = int(start_raw)
        end = int(end_raw) if end_raw else file_size - 1
    elif end_raw:
        suffix = int(end_raw)
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        return None
    end = min(end, file_size - 1)
    if start > end or start >= file_size:
        return None
    return start, end


class SmbHttpStreamServer:
    """Serves short-lived localhost URLs backed by on-demand SMB reads."""

    def __init__(self, smb_file_repository: SmbFileRepository) -> None:
        self._repo = smb_file_repository
        self._lock = threading.RLock()
        self._streams: dict[str, _StreamEntry] = {}
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port = 0

    def resolve_stream_uri(self, absolute_path: PurePosixPath) -> str:
        size = self._repo.file_size(absolute_path)
        if size is None:
            raise FileNotFoundError(f"SMB file not found: {absolute_path}")

        content_type = mimetypes.guess_type(absolute_path.name)[0] or "application/octet-stream"
        token = uuid.uuid4().hex
        entry = _StreamEntry(path=absolute_path, size=size, content_type=content_type)
        with self._lock:
            self._streams[token] = entry
            self._ensure_running()
        filename = absolute_path.name.replace("/", "_")
        return f"http://127.0.0.1:{self._port}/stream/{token}/{filename}"

    def shutdown(self) -> None:
        with self._lock:
            self._streams.clear()
            server = self._server
            self._server = None
            self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()

    def _ensure_running(self) -> None:
        if self._server is not None:
            return

        handler = _make_handler(self)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, name="smb-http-stream", daemon=True)
        thread.start()
        self._server = server
        self._thread = thread
        self._port = server.server_address[1]
        logger.info("SMB HTTP stream server listening on 127.0.0.1:%s", self._port)

    def _lookup(self, token: str) -> _StreamEntry | None:
        with self._lock:
            return self._streams.get(token)

    def _read(self, entry: _StreamEntry, offset: int, length: int) -> bytes | None:
        return self._repo.read_file_range(entry.path, offset, length)


def _make_handler(server: SmbHttpStreamServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            logger.debug("stream %s - %s", self.address_string(), format % args)

        def _write_stream(self, entry: _StreamEntry, offset: int, length: int) -> None:
            remaining = length
            pos = offset
            while remaining > 0:
                to_read = min(_READ_CHUNK, remaining)
                data = server._read(entry, pos, to_read)
                if not data:
                    break
                try:
                    self.wfile.write(data)
                except BrokenPipeError:
                    return
                pos += len(data)
                remaining -= len(data)

        def do_GET(self) -> None:  # noqa: N802
            parts = self.path.split("/")
            if len(parts) < 4 or parts[1] != "stream":
                self.send_error(404)
                return

            token = parts[2]
            entry = server._lookup(token)
            if entry is None:
                self.send_error(404)
                return

            byte_range = parse_byte_range(self.headers.get("Range"), entry.size)
            if byte_range is None:
                self.send_response(200)
                self.send_header("Content-Type", entry.content_type)
                self.send_header("Content-Length", str(entry.size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self._write_stream(entry, 0, entry.size)
                return

            start, end = byte_range
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", entry.content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Content-Range", f"bytes {start}-{end}/{entry.size}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self._write_stream(entry, start, length)

    return Handler
