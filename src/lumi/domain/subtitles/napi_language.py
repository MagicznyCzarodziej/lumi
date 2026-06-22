"""NapiProjekt API language codes."""

from __future__ import annotations

NAPI_LANGUAGE_ALIASES = {
    "EN": "ENG",
    "ENG": "ENG",
    "PL": "POL",
    "POL": "POL",
}
DEFAULT_NAPI_LANGUAGE = "ENG"


def normalize_napi_language(language: str) -> str:
    normalized = language.strip().upper()
    return NAPI_LANGUAGE_ALIASES.get(normalized, normalized)
