from __future__ import annotations

from lumi.infrastructure.subtitles.napi_encoding import decode_subtitle_bytes


def test_decode_subtitle_bytes_prefers_utf8_polish() -> None:
    text = "ąćęłńóśżź"
    assert decode_subtitle_bytes(text.encode("utf-8")) == text


def test_decode_subtitle_bytes_handles_ascii_english() -> None:
    text = "1\n00:00:01,000 --> 00:00:03,000\nHello world\n"
    assert decode_subtitle_bytes(text.encode("windows-1252")) == text


def test_decode_subtitle_bytes_uses_chardet() -> None:
    text = "1\n00:00:01,000 --> 00:00:03,000\nCafé\n"
    assert decode_subtitle_bytes(text.encode("utf-8")) == text
