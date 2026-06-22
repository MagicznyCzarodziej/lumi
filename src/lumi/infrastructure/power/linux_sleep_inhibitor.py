"""Block system suspend on Linux via systemd-logind."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class LinuxSleepInhibitor:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None

    def acquire(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        self._process = None
        if shutil.which("systemd-inhibit") is None:
            logger.debug("systemd-inhibit not found; sleep will not be inhibited")
            return
        try:
            self._process = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--what=sleep:idle",
                    "--who=Lumi",
                    "--why=Video playback",
                    "--mode=block",
                    "sleep",
                    "infinity",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            logger.warning("Failed to inhibit system sleep: %s", exc)

    def release(self) -> None:
        proc = self._process
        self._process = None
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
