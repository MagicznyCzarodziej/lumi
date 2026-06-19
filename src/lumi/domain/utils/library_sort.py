"""Library entry ordering helpers."""

from __future__ import annotations

from lumi.domain.library.models import LibraryEntry
from lumi.domain.utils.natural_order_comparator import normalize_for_library_sort


def sort_library_entries(entries: list[LibraryEntry]) -> list[LibraryEntry]:
    return sorted(entries, key=lambda entry: normalize_for_library_sort(entry.name.name))
