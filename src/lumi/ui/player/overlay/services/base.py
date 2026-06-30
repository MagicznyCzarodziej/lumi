from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay
    from lumi.ui.player.overlay.runtime import OverlayRuntime


class OverlayService:
    __slots__ = ("_overlay",)

    def __init__(self, overlay: PlayerOverlay) -> None:
        self._overlay = overlay

    @property
    def _o(self) -> PlayerOverlay:
        return self._overlay

    @property
    def _rt(self) -> OverlayRuntime:
        return self._overlay._rt

    def _update(self) -> None:
        self._overlay.update()
