"""File and folder name parsing."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from lumi.domain.library.building.patterns import (
    EPISODE_FILE_PATTERN,
    NAME_WITH_ALTERNATIVE_NAME_PATTERN,
    ORDINAL_NUMBER_PATTERN,
    ORDINAL_NUMBER_PREFIX,
    SEASON_NUMBER_PATTERN,
)
from lumi.domain.library.models import Name

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EpisodeDetails:
    number: int
    title: str


def _normalize_extension(extension: str) -> str:
    return extension.lower().lstrip(".")


def _normalize_extensions(video_extensions: set[str]) -> set[str]:
    return {_normalize_extension(ext) for ext in video_extensions}


def parse_episode_details(
    file_name: str,
    video_extensions: set[str],
    series_name: str,
) -> EpisodeDetails:
    matcher = EPISODE_FILE_PATTERN.matches(file_name)
    file_base_name = _get_file_base_name(file_name, video_extensions)
    episode_name_without_series_name = file_base_name.removeprefix(f"{series_name} - ")

    try:
        if matcher.matches():
            episode_number_text = matcher.group("episodeNumber")
            if episode_number_text is None:
                raise RuntimeError(f"Missing episode number in: {file_name}")
            return EpisodeDetails(int(episode_number_text), episode_name_without_series_name)

        for candidate in (episode_name_without_series_name, file_base_name):
            if (number := extract_leading_episode_number(candidate)) is not None:
                title = episode_name_without_series_name or file_base_name
                return EpisodeDetails(number, title)

        raise RuntimeError(f"Episode file name does not match episode pattern: {file_name}")
    except Exception as exc:
        logger.warning("Error while trying to parse episode title: %s", file_name, exc_info=exc)
        return EpisodeDetails(-1, episode_name_without_series_name or file_base_name)


def parse_name(folder_name: str) -> Name:
    match = NAME_WITH_ALTERNATIVE_NAME_PATTERN.matches(folder_name)

    if match.matches():
        main_name = match.group("mainName")
        alt_name = match.group("alternativeName")
        if main_name is None or alt_name is None:
            raise RuntimeError(f"Invalid alternative name pattern: {folder_name}")
        main_name = ORDINAL_NUMBER_PREFIX.sub("", main_name.strip())
        return Name(main_name, alt_name.strip())

    trimmed = folder_name.strip()
    return Name(ORDINAL_NUMBER_PREFIX.sub("", trimmed))


def extract_season_number(name: str) -> int | None:
    matcher = SEASON_NUMBER_PATTERN.matches(name)
    if not matcher.find():
        return None
    for group in ("g1", "g2", "g3"):
        value = matcher.group(group)
        if value is not None:
            return int(value)
    return None


def extract_season_number_from_episode(file_name: str) -> int | None:
    matcher = EPISODE_FILE_PATTERN.matches(file_name)
    if not matcher.matches():
        return None
    season_number_text = matcher.group("seasonNumber")
    if season_number_text is None:
        return None
    return int(season_number_text)


def get_ordinal_number_from_name(name: str) -> int | None:
    matcher = ORDINAL_NUMBER_PATTERN.matches(name)
    if not matcher.find():
        return None
    number_text = matcher.group("number")
    if number_text is None:
        return None
    return int(number_text)


def extract_leading_episode_number(text: str) -> int | None:
    stripped = text.strip()
    if not stripped:
        return None
    if (number := get_ordinal_number_from_name(stripped)) is not None:
        return number
    bracket_match = re.match(r"^\[(?P<number>\d+)\]", stripped)
    if bracket_match is not None:
        return int(bracket_match.group("number"))
    dash_match = re.match(r"^(?P<number>\d+)\s*-\s", stripped)
    if dash_match is not None:
        return int(dash_match.group("number"))
    return None


def resolve_season_ordinal_number(
    name: str,
    *,
    episode_file_names: tuple[str, ...] = (),
    fallback_number: int | None = None,
) -> int:
    if (number := extract_season_number(name)) is not None:
        return number
    if (number := get_ordinal_number_from_name(name)) is not None:
        return number
    season_numbers = {
        number
        for file_name in episode_file_names
        if (number := extract_season_number_from_episode(file_name)) is not None
    }
    if len(season_numbers) == 1:
        return next(iter(season_numbers))
    if fallback_number is not None:
        return fallback_number
    return 0


def is_video_file(file_name: str, video_extensions: set[str]) -> bool:
    extension = _normalize_extension(file_name.rsplit(".", 1)[-1] if "." in file_name else "")
    return extension in _normalize_extensions(video_extensions)


def _get_file_base_name(file_name: str, video_extensions: set[str]) -> str:
    extension = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
    normalized = _normalize_extensions(video_extensions)
    if _normalize_extension(extension) in normalized:
        return file_name[: -(len(extension) + 1)]
    return file_name.rsplit(".", 1)[0]
