"""Shared ID helpers."""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from lumi.domain.library.models import EntryId

_LUMI_ENTRY_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def entry_id_from_path(path: PurePosixPath) -> EntryId:
    """Stable entry ID derived from a share path (survives library rebuilds)."""
    normalized = path.as_posix()
    return EntryId(id=str(uuid.uuid5(_LUMI_ENTRY_ID_NAMESPACE, normalized)))
