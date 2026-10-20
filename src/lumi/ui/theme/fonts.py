"""Bundled UI fonts (A3 prototype: DM Sans + JetBrains Mono)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

_FONTS_DIR = Path(__file__).parent / "fonts"
_UI_FAMILY = "DM Sans"
_MONO_FAMILY = "JetBrains Mono"


def install_ui_fonts() -> tuple[str, str]:
    """Register bundled fonts; return (ui family, mono family) for QSS and QFont."""
    ui_family = _UI_FAMILY
    mono_family = _MONO_FAMILY
    for path in sorted(_FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            continue
        registered = families[0]
        if "Mono" in path.name or "mono" in registered.lower():
            mono_family = registered
        else:
            ui_family = registered
    return ui_family, mono_family


def apply_app_fonts(app: QApplication) -> tuple[str, str]:
    """Set default application font to DM Sans."""
    ui_family, mono_family = install_ui_fonts()
    app.setFont(QFont(ui_family))
    return ui_family, mono_family
