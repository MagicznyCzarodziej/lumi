"""Base class for router-managed screens."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import Destination


class NavigableScreen(QWidget):
    back_requested = Signal()

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        raise NotImplementedError

    def focus_default(self) -> None:
        """Move keyboard focus to this screen's primary control."""
