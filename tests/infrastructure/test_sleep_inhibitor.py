"""Tests for sleep inhibition."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lumi.infrastructure.power.linux_sleep_inhibitor import LinuxSleepInhibitor
from lumi.infrastructure.power.noop_sleep_inhibitor import NoopSleepInhibitor


def test_noop_sleep_inhibitor_is_harmless() -> None:
    inhibitor = NoopSleepInhibitor()
    inhibitor.acquire()
    inhibitor.release()


@patch("lumi.infrastructure.power.linux_sleep_inhibitor.subprocess.Popen")
@patch("lumi.infrastructure.power.linux_sleep_inhibitor.shutil.which", return_value="/usr/bin/systemd-inhibit")
def test_linux_sleep_inhibitor_starts_systemd_inhibit(which: MagicMock, popen: MagicMock) -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    popen.return_value = proc

    inhibitor = LinuxSleepInhibitor()
    inhibitor.acquire()

    which.assert_called_once_with("systemd-inhibit")
    popen.assert_called_once()
    args = popen.call_args.args[0]
    assert args[0] == "systemd-inhibit"
    assert "--what=sleep:idle" in args
    inhibitor.release()
    proc.terminate.assert_called_once()


@patch("lumi.infrastructure.power.linux_sleep_inhibitor.shutil.which", return_value=None)
def test_linux_sleep_inhibitor_skips_when_unavailable(_which: MagicMock) -> None:
    inhibitor = LinuxSleepInhibitor()
    inhibitor.acquire()
    inhibitor.release()
