from __future__ import annotations

from lumi.domain.subtitles.napi_language import normalize_napi_language


def test_normalize_napi_language_maps_short_codes() -> None:
    assert normalize_napi_language("en") == "ENG"
    assert normalize_napi_language("pl") == "POL"
    assert normalize_napi_language("ENG") == "ENG"
