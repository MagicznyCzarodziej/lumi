"""Overlay command handlers — one module per Command, registered on import."""

from __future__ import annotations

from . import browse, playback, scrub, tracks, video, view, volume
from .handle_hit import handle_hit
from .press_key import press_key_for_command
from .processor import process_command

__all__ = [
    "handle_hit",
    "press_key_for_command",
    "process_command",
]

# Import side effects: each subpackage registers its command handlers on load.
_ = (browse, playback, scrub, tracks, video, view, volume)
