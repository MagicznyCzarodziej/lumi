"""Prototype catalog token parity (issue #10)."""

from __future__ import annotations

from lumi.ui.theme import colors, spacing


def test_global_tokens_match_a3_catalog() -> None:
    assert colors.BACKGROUND == "#07080F"
    assert colors.POSTER_BED == "#0A0A12"
    assert spacing.TAG_CHIP_RADIUS == 9999
    assert spacing.TOPBAR_ICON_RADIUS == spacing.CORNER_RADIUS_SM
    assert spacing.FOCUS_RING_WIDTH == spacing.ALPHABET_FOCUS_RING_WIDTH
    assert spacing.RECENT_WATCH_THUMBNAIL_WIDTH == spacing.s(98)
    assert spacing.RECENT_WATCH_THUMBNAIL_HEIGHT == spacing.s(149)
