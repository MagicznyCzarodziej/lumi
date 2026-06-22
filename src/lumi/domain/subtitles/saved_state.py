"""Track whether a NapiProjekt subtitle was saved to the library share."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Protocol


class NapiSavedStateStore(Protocol):
    def is_saved_to_nas(self, video_path: PurePosixPath) -> bool: ...

    def mark_saved_to_nas(self, video_path: PurePosixPath) -> None: ...

    def clear(self, video_path: PurePosixPath) -> None: ...
