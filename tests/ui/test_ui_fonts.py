"""Bundled DM Sans loads for library UI."""

from __future__ import annotations

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from lumi.ui.theme.fonts import install_ui_fonts


def test_dm_sans_font_is_registered(qtbot) -> None:
    QApplication.instance() or QApplication([])
    ui_family, _mono = install_ui_fonts()
    families = set(QFontDatabase.families())
    assert ui_family in families
    assert "DM" in ui_family or ui_family == "DM Sans"
