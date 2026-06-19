"""QSS rendering and theme application."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget

from lumi.ui.theme import colors, spacing, typography

_THEME_DIR = Path(__file__).parent
_TOKEN_PATTERN = re.compile(r"@([A-Z][A-Z0-9_]*)@")


def _token_map() -> dict[str, str]:
    tokens: dict[str, str] = {}
    for module in (colors, spacing, typography):
        for key, value in vars(module).items():
            if key.isupper():
                tokens[key] = str(value)
    return tokens


def render_qss(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    tokens = _token_map()

    def replace_token(match: re.Match[str]) -> str:
        return tokens.get(match.group(1), match.group(0))

    return _TOKEN_PATTERN.sub(replace_token, text)


def apply_global_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(render_qss(_THEME_DIR / "qss" / "global.qss"))


def apply_widget_stylesheet(widget: QWidget, qss_path: Path) -> None:
    widget.setStyleSheet(render_qss(qss_path))
