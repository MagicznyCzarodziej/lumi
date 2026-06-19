"""Stack-based screen router."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget

from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import Destination, LIBRARY
from lumi.ui.navigation.navigable_screen import NavigableScreen

ScreenFactory = Callable[[], NavigableScreen]


class Router(QObject):
    destination_changed = Signal(object)

    def __init__(self, stack: QStackedWidget, context: ScreenContext) -> None:
        super().__init__()
        self._stack = stack
        self._context = context
        self._history: list[Destination] = []
        self._screens: dict[str, NavigableScreen] = {}
        self._factories: dict[type, ScreenFactory] = {}

    def register(self, destination_type: type, factory: ScreenFactory) -> None:
        self._factories[destination_type] = factory

    @property
    def current(self) -> Destination | None:
        return self._history[-1] if self._history else None

    def can_pop(self) -> bool:
        return len(self._history) > 1

    def start(self, destination: Destination) -> None:
        self._history = [destination]
        self._show(destination)

    def push(self, destination: Destination) -> None:
        self._history.append(destination)
        self._show(destination)

    def pop(self) -> bool:
        if not self.can_pop():
            return False
        self._history.pop()
        self._show(self._history[-1])
        return True

    def reset_to(self, destination: Destination) -> None:
        """Clear detail screens and navigation history after library reload."""
        library_key = type(LIBRARY).__name__
        keys_to_remove = [key for key in self._screens if key != library_key]
        for key in keys_to_remove:
            screen = self._screens.pop(key)
            self._stack.removeWidget(screen)
            screen.deleteLater()
        self._history = [destination]
        self._show(destination)

    def _show(self, destination: Destination) -> None:
        screen = self._screen_for(destination)
        screen.bind(destination, self._context)
        self._stack.setCurrentWidget(screen)
        screen.focus_default()
        self.destination_changed.emit(destination)

    def _screen_for(self, destination: Destination) -> NavigableScreen:
        cache_key = type(destination).__name__
        if cache_key not in self._screens:
            factory = self._factories.get(type(destination))
            if factory is None:
                raise KeyError(f"No screen registered for {cache_key}")
            screen = factory()
            screen.back_requested.connect(self.pop)
            self._screens[cache_key] = screen
            self._stack.addWidget(screen)
        return self._screens[cache_key]
