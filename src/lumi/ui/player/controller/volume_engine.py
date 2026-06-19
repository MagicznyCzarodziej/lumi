"""Volume key-hold ramp (no Qt dependencies)."""


class VolumeEngine:
    MIN_STEP = 1.0
    MAX_STEP = 12.0
    RAMP_MS = 2800

    @classmethod
    def step(cls, elapsed_ms: int, *, step_base: int = 1) -> float:
        ramp = max(1, cls.RAMP_MS)
        t = min(1.0, elapsed_ms / ramp)
        eased = t * t * t
        unit = cls.MIN_STEP + eased * (cls.MAX_STEP - cls.MIN_STEP)
        return unit * step_base
