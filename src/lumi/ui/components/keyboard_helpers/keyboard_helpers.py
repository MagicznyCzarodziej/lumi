"""Shared keyboard helpers for library navigation widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

_ESCAPE_KEYS = frozenset({Qt.Key.Key_Escape, Qt.Key.Key_QuoteLeft})
_BACK_KEYS = _ESCAPE_KEYS | {Qt.Key.Key_Backspace}


def is_escape_key(key: int) -> bool:
    """Return True for Escape and grave/backtick (`)."""
    return key in _ESCAPE_KEYS


def is_back_key(key: int) -> bool:
    """Return True for Escape, `, and Backspace."""
    return key in _BACK_KEYS


_MODIFIER_MASK = (
    Qt.KeyboardModifier.ControlModifier
    | Qt.KeyboardModifier.AltModifier
    | Qt.KeyboardModifier.MetaModifier
)


def search_character(event: QKeyEvent) -> str | None:
    """Return typed a–z/A–Z, 0–9, or space for unmodified keys, else None."""
    if event.modifiers() & _MODIFIER_MASK:
        return None
    text = event.text()
    if len(text) == 1 and (text.isalpha() or text.isdigit() or text == " "):
        return text
    if event.key() == Qt.Key.Key_Space:
        return " "
    return None


def letter_key(event: QKeyEvent) -> str | None:
    """Return A–Z or # for unmodified letter keys, else None."""
    if event.modifiers() & _MODIFIER_MASK:
        return None
    text = event.text()
    if len(text) != 1:
        return None
    if text == "#":
        return "#"
    upper = text.upper()
    if upper.isalpha():
        return upper
    return None
