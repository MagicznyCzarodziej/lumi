"""Regex patterns for library parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Match, Pattern


@dataclass(frozen=True)
class RegexMatch:
    _match: Match[str] | None

    def matches(self) -> bool:
        return self._match is not None

    def find(self) -> bool:
        return self._match is not None

    def group(self, name: str | int) -> str | None:
        if self._match is None:
            return None
        return self._match.group(name)


@dataclass(frozen=True)
class ReadableRegexPattern:
    _exact: Pattern[str]
    _search: Pattern[str] | None = None

    def matches_text_exactly(self, text: str) -> bool:
        return self._exact.fullmatch(text) is not None

    def matches(self, text: str) -> RegexMatch:
        if self._search is not None:
            return RegexMatch(self._search.search(text))
        return RegexMatch(self._exact.fullmatch(text))


ORDINAL_NUMBER_PATTERN = ReadableRegexPattern(
    _exact=re.compile(r"^\[\d+\]\s$"),
    _search=re.compile(r"^\[(?P<number>\d+)\]\s*"),
)

SEASON_NUMBER_PATTERN = ReadableRegexPattern(
    _exact=re.compile(
        r"^(?:Season\s+(?P<g1>\d+)|S(?P<g2>\d+)|(?P<g3>\d+))$",
        re.IGNORECASE,
    ),
    _search=re.compile(
        r"(?:Season\s+(?P<g1>\d+)|S(?P<g2>\d+)|(?P<g3>\d+))",
        re.IGNORECASE,
    ),
)

EPISODE_FILE_PATTERN = ReadableRegexPattern(
    _exact=re.compile(
        r"^.*?\s+-\s+S(?P<seasonNumber>\d{2})E(?P<episodeNumber>\d{2})(?:\s+.*)?\.\w+$",
        re.IGNORECASE,
    ),
)

NAME_WITH_ALTERNATIVE_NAME_PATTERN = ReadableRegexPattern(
    _exact=re.compile(r"^(?P<mainName>.*?)\s*\((?P<alternativeName>.*?)\)\s*$"),
)

ORDINAL_NUMBER_PREFIX = re.compile(r"^\[\d+\]\s")
