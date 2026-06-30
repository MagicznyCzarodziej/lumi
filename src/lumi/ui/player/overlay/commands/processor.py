"""Command dispatch registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from lumi.ui.player.overlay.input_router import Command, RoutedCommand

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay

CommandHandler = Callable[["PlayerOverlay", RoutedCommand], None]

_HANDLERS: dict[Command, CommandHandler] = {}


def register(command: Command, handler: CommandHandler) -> None:
    _HANDLERS[command] = handler


def process_command(overlay: PlayerOverlay, cmd: RoutedCommand) -> None:
    handler = _HANDLERS.get(cmd.command)
    if handler is not None:
        handler(overlay, cmd)


def refresh_panel(overlay: PlayerOverlay) -> None:
    overlay.panel.rebuild()
    overlay.panel.ensure_panel_focus_visible()
    overlay.activity.note_ui_activity()
    overlay.update()


def show_panel(overlay: PlayerOverlay) -> None:
    overlay.show()
    overlay.raise_()
    rt = overlay._rt
    rt.hide_timer.stop()
    rt.dim_timer.stop()
    rt.ui_opacity = 1.0
