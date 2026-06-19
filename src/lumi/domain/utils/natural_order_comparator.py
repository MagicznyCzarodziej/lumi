"""Comparator that ignores articles (a, an, the) for library sorting."""

from __future__ import annotations

_ARTICLES = ("a ", "an ", "the ")


def normalize_for_library_sort(value: str) -> str:
    lowercase = value.strip().lower()
    for article in _ARTICLES:
        if lowercase.startswith(article):
            return lowercase[len(article) :].strip()
    return lowercase


def library_style_compare(left: str, right: str) -> int:
    normalized_left = normalize_for_library_sort(left)
    normalized_right = normalize_for_library_sort(right)
    if normalized_left < normalized_right:
        return -1
    if normalized_left > normalized_right:
        return 1
    return 0
