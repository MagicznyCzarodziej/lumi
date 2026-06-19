"""Press feedback animation timing (no Qt)."""

from __future__ import annotations

from dataclasses import dataclass

ATTACK_MS = 70
DECAY_MS = 240


@dataclass
class PressAnimation:
    key: str
    holding: bool = True
    released_ms: int | None = None


def press_strength(anim: PressAnimation, elapsed_ms: int) -> float:
    """Return 0..1 pulse strength for background highlight."""
    if anim.holding:
        t = min(1.0, elapsed_ms / ATTACK_MS)
        return t * t

    if anim.released_ms is None:
        return 0.0

    decay_elapsed = max(0, elapsed_ms - anim.released_ms)
    if decay_elapsed >= DECAY_MS:
        return 0.0

    t = 1.0 - decay_elapsed / DECAY_MS
    return t * t


def release(anim: PressAnimation, elapsed_ms: int) -> PressAnimation:
    if not anim.holding:
        return anim
    return PressAnimation(key=anim.key, holding=False, released_ms=elapsed_ms)
