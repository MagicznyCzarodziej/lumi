"""Subtitle text decoding ported from napi-py encoding heuristics."""

from __future__ import annotations

import logging

import chardet

from lumi.domain.subtitles.provider import SubtitleDownloadError

logger = logging.getLogger(__name__)

DECODING_ORDER = (
    "utf-16",
    "windows-1250",
    "windows-1251",
    "windows-1252",
    "windows-1253",
    "windows-1254",
    "utf-8",
)
CHECK_NUM_CHARS = 5000
AUTO_DETECT_THRESHOLD = 0.9


def _is_ascii(char: str) -> bool:
    return ord(char) < 128


def _is_polish_diacritic(char: str) -> bool:
    return char in "ąćęłńóśżźĄĆĘŁŃÓŚŻŹ"


def _is_correct_encoding(text: str) -> bool:
    err_symbols = 0
    diacritics = 0
    for char in text[:CHECK_NUM_CHARS]:
        if _is_polish_diacritic(char):
            diacritics += 1
        elif not _is_ascii(char):
            err_symbols += 1
    return err_symbols < diacritics


def _is_mostly_ascii(text: str) -> bool:
    sample = text[:CHECK_NUM_CHARS]
    if not sample:
        return True
    ascii_count = sum(1 for char in sample if _is_ascii(char))
    return ascii_count / len(sample) >= 0.9


def _looks_like_subtitles(text: str) -> bool:
    sample = text[:CHECK_NUM_CHARS]
    return "-->" in sample or sample.lstrip().startswith("1\n")


def decode_subtitle_bytes(data: bytes) -> str:
    try:
        utf8 = data.decode("utf-8")
        if (
            _is_correct_encoding(utf8)
            or _is_mostly_ascii(utf8)
            or _looks_like_subtitles(utf8)
        ):
            return utf8
    except UnicodeDecodeError:
        pass

    detected = chardet.detect(data)
    encoding = detected.get("encoding")
    confidence = float(detected.get("confidence") or 0.0)
    if encoding and confidence > AUTO_DETECT_THRESHOLD:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            logger.debug("chardet encoding %s failed, falling back", encoding)

    last_error: UnicodeDecodeError | None = None
    for enc in DECODING_ORDER:
        try:
            decoded = data.decode(enc)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        if (
            _is_correct_encoding(decoded)
            or _is_mostly_ascii(decoded)
            or _looks_like_subtitles(decoded)
        ):
            return decoded

    if last_error is not None:
        raise SubtitleDownloadError("Could not decode subtitle text") from last_error
    raise SubtitleDownloadError("Could not decode subtitle text")
