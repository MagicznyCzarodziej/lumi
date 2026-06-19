"""Volume ramp tests."""

from __future__ import annotations

from lumi.ui.player.controller.volume_engine import VolumeEngine


def test_volume_step_ramps_with_hold_time() -> None:
    early = VolumeEngine.step(100, step_base=1)
    late = VolumeEngine.step(VolumeEngine.RAMP_MS, step_base=1)
    assert early < late
    assert early >= VolumeEngine.MIN_STEP
    assert late <= VolumeEngine.MAX_STEP


def test_ctrl_multiplies_base_step() -> None:
    assert VolumeEngine.step(0, step_base=5) == 5.0
    assert VolumeEngine.step(VolumeEngine.RAMP_MS, step_base=5) == VolumeEngine.MAX_STEP * 5
