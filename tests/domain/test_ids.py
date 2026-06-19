"""Stable entry ID tests."""

from __future__ import annotations

from tests.constants import MOCK_LIBRARY_ROOT
from pathlib import PurePosixPath

from lumi.domain.ids import entry_id_from_path


def test_entry_id_from_path_is_stable() -> None:
    path = MOCK_LIBRARY_ROOT / "Alien"
    assert entry_id_from_path(path).id == entry_id_from_path(path).id


def test_entry_id_from_path_differs_by_path() -> None:
    left = entry_id_from_path(MOCK_LIBRARY_ROOT / "Alien")
    right = entry_id_from_path(MOCK_LIBRARY_ROOT / "Aliens")
    assert left.id != right.id
