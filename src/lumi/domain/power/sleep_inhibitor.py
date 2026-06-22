"""Prevent system sleep while video is playing."""

from __future__ import annotations

from typing import Protocol


class SleepInhibitor(Protocol):
    def acquire(self) -> None: ...

    def release(self) -> None: ...
