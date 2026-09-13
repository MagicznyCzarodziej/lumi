"""SmbFileRepository path existence tests."""

from __future__ import annotations

import threading
from pathlib import PurePosixPath
from unittest.mock import MagicMock, patch

from smbprotocol.exceptions import SMBResponseException

from lumi.infrastructure.smb.connection import SmbShareSession
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository
from tests.constants import MOCK_LIBRARY_ROOT


def test_file_exists_uses_direct_open_instead_of_directory_listing() -> None:
    session = MagicMock()
    repository = SmbFileRepository(MagicMock(), session=session)
    session.ensure_connected = MagicMock()
    tree = MagicMock()
    session.tree.return_value = tree

    with patch("lumi.infrastructure.smb.smb_file_repository._path_exists", return_value=True) as exists:
        assert repository.file_exists(MOCK_LIBRARY_ROOT / "Alien/poster.jpg") is True

    exists.assert_called_once_with(tree, MOCK_LIBRARY_ROOT / "Alien/poster.jpg")


def test_path_exists_returns_false_when_open_fails() -> None:
    from lumi.infrastructure.smb import smb_file_repository as module

    tree = MagicMock()
    file_handle = MagicMock()
    file_handle.create.side_effect = SMBResponseException(MagicMock())

    with patch.object(module, "Open", return_value=file_handle):
        assert module._path_exists(tree, MOCK_LIBRARY_ROOT / "missing.jpg") is False

    file_handle.close.assert_not_called()


def test_reconnect_for_playback_disconnects_all_sessions() -> None:
    config = MagicMock()
    session = MagicMock(spec=SmbShareSession)
    with patch("lumi.infrastructure.smb.smb_file_repository.SmbShareSession", return_value=session):
        repository = SmbFileRepository(config)
        assert repository.session is session

        repository.reconnect_for_playback()

    session.disconnect.assert_called_once()


def test_each_thread_gets_its_own_smb_session() -> None:
    config = MagicMock()
    repository = SmbFileRepository(config)
    created: list[SmbShareSession] = []

    def fake_session_factory(cfg: MagicMock) -> SmbShareSession:
        session = MagicMock(spec=SmbShareSession)
        created.append(session)
        return session

    barrier = threading.Barrier(2)
    sessions_by_thread: dict[int, SmbShareSession] = {}

    def resolve_session() -> None:
        barrier.wait()
        sessions_by_thread[threading.get_ident()] = repository.session

    with patch("lumi.infrastructure.smb.smb_file_repository.SmbShareSession", side_effect=fake_session_factory):
        threads = [threading.Thread(target=resolve_session) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert len(created) == 2
    assert len(sessions_by_thread) == 2
    assert len({id(session) for session in sessions_by_thread.values()}) == 2


def test_disconnect_extra_sessions_keeps_current_thread_session() -> None:
    config = MagicMock()
    main_session = MagicMock(spec=SmbShareSession)
    worker_session = MagicMock(spec=SmbShareSession)

    with patch("lumi.infrastructure.smb.smb_file_repository.SmbShareSession", return_value=main_session):
        repository = SmbFileRepository(config)
        assert repository.session is main_session
        with repository._sessions_lock:
            repository._sessions.append(worker_session)

        repository.disconnect_extra_sessions()

    worker_session.disconnect.assert_called_once()
    main_session.disconnect.assert_not_called()
    assert repository.session is main_session
