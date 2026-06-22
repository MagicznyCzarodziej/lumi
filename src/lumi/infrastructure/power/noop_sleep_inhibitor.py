"""No-op sleep inhibitor for platforms without suspend APIs."""

from __future__ import annotations


class NoopSleepInhibitor:
    def acquire(self) -> None:
        return

    def release(self) -> None:
        return
