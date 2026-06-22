"""Human-readable labels for mpv track-list entries."""

from __future__ import annotations

from PySide6.QtCore import QLocale

# Non-standard codes sometimes seen in media files (ISO 639-1 uses "ja", not "jp").
_LANG_ALIASES: dict[str, str] = {
    "jp": "ja",
    "cn": "zh",
    "cn1": "zh",
    "cn2": "zh",
    "chs": "zh",
    "cht": "zh",
    "uk": "en",
    "us": "en",
}

# Subtitle extensions mpv sometimes puts in the title field for external tracks.
_SUBTITLE_EXTENSIONS = frozenset({"ass", "ssa", "srt", "sub", "txt", "vtt"})

# When QLocale cannot resolve a code.
_FALLBACK_NAMES: dict[str, str] = {
    "en": "English",
    "eng": "English",
    "ja": "Japanese",
    "jpn": "Japanese",
    "jp": "Japanese",
    "de": "German",
    "ger": "German",
    "deu": "German",
    "fr": "French",
    "fre": "French",
    "fra": "French",
    "es": "Spanish",
    "spa": "Spanish",
    "it": "Italian",
    "ita": "Italian",
    "pt": "Portuguese",
    "por": "Portuguese",
    "ru": "Russian",
    "rus": "Russian",
    "ko": "Korean",
    "kor": "Korean",
    "zh": "Chinese",
    "zho": "Chinese",
    "chi": "Chinese",
    "cmn": "Chinese",
    "yue": "Chinese",
    "und": "Unknown",
}


def _is_lang_code(value: str) -> bool:
    value = value.strip().lower()
    if value in _SUBTITLE_EXTENSIONS:
        return False
    return 2 <= len(value) <= 3 and value.isalpha()


def external_subtitle_basename(track: dict) -> str:
    external = track.get("external-filename") or track.get("external_filename")
    if not external:
        return ""
    text = str(external).replace("\\", "/")
    name = text.rsplit("/", 1)[-1]
    if "?" in name:
        name = name.split("?", 1)[0]
    return name


def language_display_name(code: str | None) -> str:
    """Map ISO 639-1/639-2 language code to a UI label (e.g. en → English)."""
    if not code:
        return ""
    raw = code.strip().lower()
    if raw in ("und", "unknown", "qaa", "qad"):
        return "Unknown"

    normalized = _LANG_ALIASES.get(raw, raw)
    loc = QLocale(normalized)
    if loc.language() != QLocale.Language.C:
        name = QLocale.system().languageToString(loc.language())
        if name and name != "C":
            return name

    return _FALLBACK_NAMES.get(raw, _FALLBACK_NAMES.get(normalized, raw))


def _qualifiers(track: dict) -> list[str]:
    tags: list[str] = []
    if track.get("forced"):
        tags.append("Forced")
    if track.get("hearing-impaired"):
        tags.append("SDH")
    if track.get("visual-impaired"):
        tags.append("SDH")
    if track.get("default"):
        tags.append("Default")
    return tags


def _with_qualifiers(base: str, track: dict) -> str:
    tags = _qualifiers(track)
    if not tags:
        return base
    return f"{base} ({', '.join(tags)})"


def subtitle_track_label(track: dict, *, display_name: str | None = None) -> str:
    title = str(track.get("title") or "").strip()
    lang = str(track.get("lang") or "").strip()
    tid = track.get("id")

    if display_name:
        return _with_qualifiers(display_name, track)

    filename = external_subtitle_basename(track)
    if filename:
        return _with_qualifiers(filename, track)

    if title and not _is_lang_code(title):
        return _with_qualifiers(title, track)

    name = language_display_name(title if _is_lang_code(title) else lang)
    if name:
        return _with_qualifiers(name, track)
    if title:
        return _with_qualifiers(title, track)
    return f"Track {tid}"


def audio_track_label(track: dict) -> str:
    title = str(track.get("title") or "").strip()
    lang = str(track.get("lang") or "").strip()
    tid = track.get("id")

    if title and not _is_lang_code(title):
        label = title
        lang_name = language_display_name(lang)
        if lang_name and lang_name.lower() not in title.lower():
            label = f"{title} ({lang_name})"
        return _with_qualifiers(label, track)

    name = language_display_name(title if _is_lang_code(title) else lang)
    if name:
        return _with_qualifiers(name, track)
    if title:
        return _with_qualifiers(title, track)
    return f"Track {tid}"
