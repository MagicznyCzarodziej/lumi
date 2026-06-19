"""List row view models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import PurePosixPath
from typing import Callable

from lumi.domain.library.models import Name


class ListEntryTypeKind(Enum):
    SINGLE = auto()
    PLAYABLES_GROUP = auto()
    SERIES = auto()
    GROUPING = auto()


@dataclass(frozen=True)
class ListEntryType:
    kind: ListEntryTypeKind
    count: int = 0

    @staticmethod
    def single() -> ListEntryType:
        return ListEntryType(ListEntryTypeKind.SINGLE)

    @staticmethod
    def playables_group(size: int) -> ListEntryType:
        return ListEntryType(ListEntryTypeKind.PLAYABLES_GROUP, size)

    @staticmethod
    def series(size: int) -> ListEntryType:
        return ListEntryType(ListEntryTypeKind.SERIES, size)

    @staticmethod
    def grouping(size: int) -> ListEntryType:
        return ListEntryType(ListEntryTypeKind.GROUPING, size)


@dataclass
class ListEntryUiModel:
    name: Name
    entry_type: ListEntryType
    poster_path: PurePosixPath | None = None
    on_click: Callable[[], None] = field(default=lambda: None, repr=False)
    on_focus: Callable[[], None] = field(default=lambda: None, repr=False)


class NameDisplayStrategy(Enum):
    REGULAR = auto()
    LIBRARY = auto()
