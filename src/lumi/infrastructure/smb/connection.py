"""SMB connection helpers."""

from __future__ import annotations

import logging
import threading
import uuid
from pathlib import PurePosixPath

from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect

from lumi.config.smb_config import SmbConfig

logger = logging.getLogger(__name__)

IGNORED_NAMES = frozenset(
    {".", "..", "#recycle", "$RECYCLE.BIN", "System Volume Information"}
)


def format_smb_username(config: SmbConfig) -> str:
    """Return username with domain prefix for NTLM auth (DOMAIN\\user)."""
    username = config.username
    domain = config.domain.strip()
    if not domain or "\\" in username or "@" in username:
        return username
    return f"{domain}\\{username}"


def smb_uri_auth_user(config: SmbConfig) -> str:
    """Return domain/user auth segment for mpv smb:// URIs (forward slash, not backslash)."""
    username = config.username.strip()
    domain = config.domain.strip()
    if "\\" in username:
        return username.replace("\\", "/")
    if "@" in username:
        return username
    if domain:
        return f"{domain}/{username}"
    return username


def share_relative_path(path: PurePosixPath) -> str:
    normalized = str(path).replace("\\", "/").strip("/")
    return normalized or "."


def smb_uri(config: SmbConfig, absolute_path: PurePosixPath) -> str:
    """Build a smb:// URI for external players (mpv streams from share — no local copy)."""
    return playback_uri(config, absolute_path)


def playback_uri(config: SmbConfig, absolute_path: PurePosixPath) -> str:
    """mpv-compatible smb:// URI with credentials for direct streaming."""
    from urllib.parse import quote

    rel = share_relative_path(absolute_path)
    host = config.hostname
    share = config.share_name
    user = smb_uri_auth_user(config)
    password = config.password

    encoded_user = quote(user, safe="/")
    auth = f"{encoded_user}:{quote(password, safe='')}" if password else encoded_user
    encoded_path = "/".join(quote(part, safe="") for part in rel.split("/") if part)
    return f"smb://{auth}@{host}/{share}/{encoded_path}"


class SmbShareSession:
    """Persistent SMB connection to a single share."""

    def __init__(self, config: SmbConfig) -> None:
        self._config = config
        self._lock = threading.RLock()
        self._connection: Connection | None = None
        self._session: Session | None = None
        self._tree: TreeConnect | None = None

    @property
    def config(self) -> SmbConfig:
        return self._config

    def tree(self) -> TreeConnect:
        self.ensure_connected()
        if self._tree is None:
            raise RuntimeError("SMB tree is not connected")
        return self._tree

    def ensure_connected(self) -> None:
        with self._lock:
            if self._tree is not None:
                return

            hostname = self._config.hostname
            share_name = self._config.share_name
            logger.info("Connecting to SMB share //%s/%s", hostname, share_name)

            connection = Connection(uuid.uuid4(), hostname, 445)
            connection.connect()

            session = Session(
                connection,
                username=format_smb_username(self._config),
                password=self._config.password,
                require_encryption=False,
            )
            session.connect()

            tree = TreeConnect(session, f"\\\\{hostname}\\{share_name}")
            tree.connect()

            self._connection = connection
            self._session = session
            self._tree = tree
            logger.info("Connected to SMB share //%s/%s", hostname, share_name)

    def disconnect(self) -> None:
        with self._lock:
            if self._tree is None:
                return

            logger.info("Disconnecting from SMB share")
            try:
                self._tree.disconnect()
            except Exception:
                logger.exception("Error disconnecting SMB tree")
            try:
                if self._connection is not None:
                    self._connection.disconnect()
            except Exception:
                logger.exception("Error disconnecting SMB connection")

            self._tree = None
            self._session = None
            self._connection = None
