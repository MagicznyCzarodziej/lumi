"""SMB file listing and read access."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from io import BytesIO
from pathlib import PurePosixPath
from typing import TypeVar

from smbprotocol.exceptions import SMBResponseException
from smbprotocol.open import (
    CreateDisposition,
    CreateOptions,
    DirectoryAccessMask,
    FileAttributes,
    FileInformationClass,
    FilePipePrinterAccessMask,
    ImpersonationLevel,
    Open,
    QueryDirectoryFlags,
    ShareAccess,
)
from smbprotocol.tree import TreeConnect

from lumi.config.smb_config import SmbConfig
from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import DirectoryEntry, FilesLister
from lumi.infrastructure.smb.connection import IGNORED_NAMES, SmbShareSession, share_relative_path

logger = logging.getLogger(__name__)

T = TypeVar("T")
_READ_CHUNK_SIZE = 65536
_FILE_SHARE = ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE | ShareAccess.FILE_SHARE_DELETE
_RETRYABLE_SMB_ERRORS = (
    SMBResponseException,
    ConnectionError,
    TimeoutError,
    BrokenPipeError,
    OSError,
)
_STATUS_NO_MORE_FILES = 0x80000006


class SmbFileRepository(FilesLister, FileRepository):
    """SMB access with one connection per thread so concurrent callers do not block each other."""

    def __init__(self, config: SmbConfig, session: SmbShareSession | None = None) -> None:
        self._config = config
        self._injected_session = session
        self._thread_local = threading.local()
        self._sessions_lock = threading.Lock()
        self._sessions: list[SmbShareSession] = []
        if session is not None:
            self._sessions.append(session)

    @property
    def session(self) -> SmbShareSession:
        return self._get_session()

    def get_base_uri(self) -> str:
        return f"smb://{self._config.hostname}/{self._config.share_name}"

    def list_files_and_directories(self, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
        result = self._with_smb_retry(
            lambda session: _list_directory(session.tree(), directory_absolute_path),
            directory_absolute_path,
        )
        return result if result is not None else []

    def use_read_file_stream(
        self,
        absolute_path: PurePosixPath,
        block: Callable[[Iterator[bytes]], T],
    ) -> T | None:
        def operation(session: SmbShareSession) -> T | None:
            if not _path_exists(session.tree(), absolute_path):
                logger.warning("File does not exist: %s", absolute_path)
                return None
            return _read_file(session.tree(), absolute_path, block)

        return self._with_smb_retry(operation, absolute_path)

    def file_exists(self, absolute_path: PurePosixPath) -> bool:
        if not absolute_path.name:
            return False
        result = self._with_smb_retry(
            lambda session: _path_exists(session.tree(), absolute_path),
            absolute_path,
        )
        return bool(result)

    def read_file_bytes(self, absolute_path: PurePosixPath) -> bytes | None:
        def collect(chunks: Iterator[bytes]) -> bytes:
            return b"".join(chunks)

        return self.use_read_file_stream(absolute_path, collect)

    def file_size(self, absolute_path: PurePosixPath) -> int | None:
        return self._with_smb_retry(
            lambda session: _file_size(session.tree(), absolute_path),
            absolute_path,
        )

    def read_file_range(self, absolute_path: PurePosixPath, offset: int, length: int) -> bytes | None:
        return self._with_smb_retry(
            lambda session: _read_file_range(session.tree(), absolute_path, offset, length),
            absolute_path,
        )

    def write_file_bytes(self, absolute_path: PurePosixPath, data: bytes) -> bool:
        result = self._with_smb_retry(
            lambda session: _write_file(session.tree(), absolute_path, data),
            absolute_path,
        )
        return result is True

    def disconnect(self) -> None:
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()
        for session in sessions:
            session.disconnect()
        self._thread_local = threading.local()

    def reconnect_for_playback(self) -> None:
        """Drop cached SMB sessions (e.g. after NAS idle timeout) before streaming."""
        self.disconnect()

    def disconnect_extra_sessions(self) -> None:
        """Close SMB sessions opened by worker threads, keeping the caller's session."""
        current = getattr(self._thread_local, "session", None)
        with self._sessions_lock:
            extra = [session for session in self._sessions if session is not current]
            self._sessions = [session for session in self._sessions if session is current]
        for session in extra:
            session.disconnect()

    def _get_session(self) -> SmbShareSession:
        if self._injected_session is not None:
            return self._injected_session

        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = SmbShareSession(self._config)
            self._thread_local.session = session
            with self._sessions_lock:
                self._sessions.append(session)
        return session

    def _path_exists_on(self, session: SmbShareSession, absolute_path: PurePosixPath) -> bool:
        return _path_exists(session.tree(), absolute_path)

    def _with_smb_retry(
        self,
        operation: Callable[[SmbShareSession], T],
        absolute_path: PurePosixPath,
    ) -> T | None:
        session = self._get_session()
        for try_index in range(2):
            session.ensure_connected()
            try:
                return operation(session)
            except _RETRYABLE_SMB_ERRORS as exc:
                logger.warning(
                    "SMB operation failed for %s (attempt %d): %s",
                    share_relative_path(absolute_path),
                    try_index + 1,
                    exc,
                )
                if try_index == 0:
                    session.disconnect()
                    if self._injected_session is None:
                        self._remove_session(session)
                        session = self._get_session()
                    continue
                return None
            except Exception:
                logger.exception("Error accessing SMB path '%s'", absolute_path)
                return None
        return None

    def _remove_session(self, session: SmbShareSession) -> None:
        with self._sessions_lock:
            self._sessions = [existing for existing in self._sessions if existing is not session]
        if getattr(self._thread_local, "session", None) is session:
            self._thread_local.session = None


def _path_exists(tree: TreeConnect, absolute_path: PurePosixPath) -> bool:
    open_path = share_relative_path(absolute_path)
    file_handle = Open(tree, open_path)
    try:
        file_handle.create(
            ImpersonationLevel.Impersonation,
            FilePipePrinterAccessMask.FILE_READ_DATA | FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
            FileAttributes.FILE_ATTRIBUTE_NORMAL,
            _FILE_SHARE,
            CreateDisposition.FILE_OPEN,
            CreateOptions.FILE_NON_DIRECTORY_FILE,
        )
    except SMBResponseException as exc:
        logger.debug("SMB path not found: %s (%s)", open_path, exc)
        return False
    file_handle.close()
    return True


def _list_directory(tree: TreeConnect, directory_absolute_path: PurePosixPath) -> list[DirectoryEntry]:
    open_path = share_relative_path(directory_absolute_path)
    directory = Open(tree, open_path)
    directory.create(
        ImpersonationLevel.Impersonation,
        FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES | DirectoryAccessMask.FILE_LIST_DIRECTORY,
        FileAttributes.FILE_ATTRIBUTE_DIRECTORY,
        ShareAccess.FILE_SHARE_READ | ShareAccess.FILE_SHARE_WRITE,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_DIRECTORY_FILE,
    )

    try:
        entries: list[DirectoryEntry] = []
        flags = QueryDirectoryFlags.SMB2_RESTART_SCANS
        while True:
            restart_scan = flags == QueryDirectoryFlags.SMB2_RESTART_SCANS
            try:
                raw = directory.query_directory(
                    "*",
                    FileInformationClass.FILE_ID_BOTH_DIRECTORY_INFORMATION,
                    flags=flags,
                )
            except SMBResponseException as exc:
                if exc.status == _STATUS_NO_MORE_FILES:
                    break
                raise
            flags = 0
            if not raw:
                if restart_scan:
                    break
                continue
            for info in raw:
                name = info["file_name"].get_value().decode("utf-16-le").rstrip("\x00")
                if name in IGNORED_NAMES:
                    continue
                attrs = info["file_attributes"].get_value()
                is_directory = bool(attrs & FileAttributes.FILE_ATTRIBUTE_DIRECTORY)
                child_path = directory_absolute_path / name
                entries.append(
                    DirectoryEntry(
                        name=name,
                        absolute_path=child_path,
                        is_directory=is_directory,
                        is_file=not is_directory,
                    )
                )
        return entries
    finally:
        directory.close()


def _read_file(
    tree: TreeConnect,
    absolute_path: PurePosixPath,
    block: Callable[[Iterator[bytes]], T],
) -> T:
    open_path = share_relative_path(absolute_path)
    file_handle = Open(tree, open_path)
    file_handle.create(
        ImpersonationLevel.Impersonation,
        FilePipePrinterAccessMask.FILE_READ_DATA | FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
        FileAttributes.FILE_ATTRIBUTE_NORMAL,
        _FILE_SHARE,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_NON_DIRECTORY_FILE,
    )

    try:
        def chunk_iterator() -> Iterator[bytes]:
            offset = 0
            while True:
                data = file_handle.read(offset, _READ_CHUNK_SIZE)
                if not data:
                    return
                yield data
                offset += len(data)
                if len(data) < _READ_CHUNK_SIZE:
                    return

        return block(chunk_iterator())
    finally:
        file_handle.close()


def _file_size(tree: TreeConnect, absolute_path: PurePosixPath) -> int:
    open_path = share_relative_path(absolute_path)
    file_handle = Open(tree, open_path)
    file_handle.create(
        ImpersonationLevel.Impersonation,
        FilePipePrinterAccessMask.FILE_READ_DATA | FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
        FileAttributes.FILE_ATTRIBUTE_NORMAL,
        _FILE_SHARE,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_NON_DIRECTORY_FILE,
    )
    try:
        return int(file_handle.end_of_file)
    finally:
        file_handle.close()


def _read_file_range(tree: TreeConnect, absolute_path: PurePosixPath, offset: int, length: int) -> bytes:
    open_path = share_relative_path(absolute_path)
    file_handle = Open(tree, open_path)
    file_handle.create(
        ImpersonationLevel.Impersonation,
        FilePipePrinterAccessMask.FILE_READ_DATA | FilePipePrinterAccessMask.FILE_READ_ATTRIBUTES,
        FileAttributes.FILE_ATTRIBUTE_NORMAL,
        _FILE_SHARE,
        CreateDisposition.FILE_OPEN,
        CreateOptions.FILE_NON_DIRECTORY_FILE,
    )
    try:
        chunks: list[bytes] = []
        remaining = length
        pos = offset
        max_read = file_handle.connection.max_read_size
        while remaining > 0:
            to_read = min(remaining, max_read)
            data = file_handle.read(pos, to_read)
            if not data:
                break
            chunk = bytes(data)
            chunks.append(chunk)
            pos += len(chunk)
            remaining -= len(chunk)
            if len(chunk) < to_read:
                break
        return b"".join(chunks)
    finally:
        file_handle.close()


def _write_file(tree: TreeConnect, absolute_path: PurePosixPath, data: bytes) -> bool:
    open_path = share_relative_path(absolute_path)
    file_handle = Open(tree, open_path)
    file_handle.create(
        ImpersonationLevel.Impersonation,
        FilePipePrinterAccessMask.FILE_WRITE_DATA
        | FilePipePrinterAccessMask.FILE_WRITE_ATTRIBUTES
        | FilePipePrinterAccessMask.FILE_WRITE_EA,
        FileAttributes.FILE_ATTRIBUTE_NORMAL,
        _FILE_SHARE,
        CreateDisposition.FILE_OVERWRITE_IF,
        CreateOptions.FILE_NON_DIRECTORY_FILE,
    )
    try:
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + _READ_CHUNK_SIZE]
            file_handle.write(chunk, offset)
            offset += len(chunk)
        return True
    finally:
        file_handle.close()


def bytes_iterator_to_stream(chunks: Iterator[bytes]) -> BytesIO:
    return BytesIO(b"".join(chunks))
