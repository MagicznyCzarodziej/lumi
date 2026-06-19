"""Library model and JSON compatibility tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumi.domain.library.models import Name, StandaloneFilm, compute_sort_name
from lumi.domain.library.serialization import library_from_json, library_to_json

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/lumi/infrastructure/mock/fixtures/mock_library.json"
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("The Batman", "Batman, The"),
        ("the Batman", "Batman, the"),
        ("A Clockwork Orange", "Clockwork Orange, A"),
        ("An American Werewolf in London", "American Werewolf in London, An"),
        ("Batman", "Batman"),
    ],
)
def test_sort_name_articles(name: str, expected: str) -> None:
    assert Name(name).sort_name == expected
    assert compute_sort_name(name) == expected


def test_mock_library_json_deserializes() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    library = library_from_json(text)
    raw = json.loads(text)
    assert len(library.entries) == len(raw["entries"])


def test_mock_library_entry_ids_preserved() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    library = library_from_json(text)
    raw_ids = [entry["id"]["id"] for entry in json.loads(text)["entries"]]
    loaded_ids = [entry.id.id for entry in library.entries]
    assert loaded_ids == raw_ids


def test_mock_library_round_trip_entry_count() -> None:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    library = library_from_json(text)
    round_trip = library_from_json(library_to_json(library))
    assert len(round_trip.entries) == len(library.entries)
    assert [entry.id.id for entry in round_trip.entries] == [entry.id.id for entry in library.entries]


def test_standalone_film_fields_from_fixture() -> None:
    library = library_from_json(FIXTURE_PATH.read_text(encoding="utf-8"))
    alien = next(entry for entry in library.entries if entry.id.id == "alien")
    assert isinstance(alien, StandaloneFilm)
    assert alien.name.name == "Alien"
    assert alien.tags == frozenset({"sci-fi", "horror"})
    assert len(alien.video_files) == 1
