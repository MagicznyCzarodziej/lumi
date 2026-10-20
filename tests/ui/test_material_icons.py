"""Material icon paths stay aligned with A3 HTML prototypes."""

from __future__ import annotations

import re
from pathlib import Path

from lumi.ui.icons.material_icons import _SVG_PATHS, IconKind


def _prototype_recent_history_path() -> str:
    html = (
        Path(__file__).resolve().parents[2]
        / "src/lumi/ui/screens/library/prototype/mockups/library-home.html"
    ).read_text(encoding="utf-8")
    match = re.search(r'id="recentBtn"[^>]*>.*?<path d="([^"]+)"', html, re.DOTALL)
    assert match is not None
    return match.group(1)


def test_history_icon_matches_library_prototype_recent_button() -> None:
    prototype = _prototype_recent_history_path()
    app_path = _SVG_PATHS[IconKind.HISTORY]

    assert app_path.startswith("M13 3c-4.97")
    assert "4.28 2.54" in app_path
    assert "4.28 2.54" in prototype
    assert "8.95 8" not in app_path
