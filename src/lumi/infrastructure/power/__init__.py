"""Platform sleep inhibition."""

from __future__ import annotations

import sys

from lumi.domain.power.sleep_inhibitor import SleepInhibitor
from lumi.infrastructure.power.noop_sleep_inhibitor import NoopSleepInhibitor


def create_sleep_inhibitor() -> SleepInhibitor:
    if sys.platform.startswith("linux"):
        from lumi.infrastructure.power.linux_sleep_inhibitor import LinuxSleepInhibitor

        return LinuxSleepInhibitor()
    return NoopSleepInhibitor()
