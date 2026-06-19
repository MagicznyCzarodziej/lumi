"""Typography design tokens."""

from lumi.ui.theme.scale import UI_SCALE, scaled as s

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, sans-serif"

# List rows + library top bar (search, filters) — 20% larger than other chrome.
_LIST_TOPBAR_EXTRA = 1.2


def _list_topbar_scaled(value: int | float) -> int:
    return max(1, round(float(value) * UI_SCALE * _LIST_TOPBAR_EXTRA))


FONT_SIZE_XS = s(11)
FONT_SIZE_SM = s(12)
FONT_SIZE_MD = s(14)
FONT_SIZE_BASE = s(15)
SIDEBAR_MENU_FONT_SIZE = FONT_SIZE_BASE
FONT_SIZE_LG = s(16)
FONT_SIZE_XL = s(18)
FONT_SIZE_TOPBAR = _list_topbar_scaled(20)
FONT_SIZE_LIST = _list_topbar_scaled(22)
FONT_SIZE_LIST_ALT = _list_topbar_scaled(12)
FONT_SIZE_HEADER = s(28)
FONT_SIZE_HEADER_BREADCRUMBS = s(22)
FONT_SIZE_HEADER_TITLE = s(34)
FONT_SIZE_HEADER_SUBTITLE = s(18)
FONT_SIZE_COUNT = _list_topbar_scaled(14)
FONT_SIZE_ALPHABET = s(17)
