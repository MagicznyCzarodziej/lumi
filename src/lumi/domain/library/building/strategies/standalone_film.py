"""Standalone film classification strategy."""

from __future__ import annotations

from lumi.domain.ids import entry_id_from_path
from lumi.domain.library.building.file_name_parser import is_video_file, parse_name
from lumi.domain.library.building.strategies.classifier import ClassificationContext, MediaClassifierStrategy
from lumi.domain.library.models import LibraryEntry, Name, StandaloneFilm, VideoFile


class StandaloneFilmStrategy:
    def is_applicable(self, context: ClassificationContext) -> bool:
        return bool(context.video_files) and not context.subdirectories

    def classify(self, context: ClassificationContext) -> LibraryEntry:
        video_files = sorted(
            (
                VideoFile(name=Name(entry.name), absolute_path=entry.absolute_path)
                for entry in context.video_files
            ),
            key=lambda vf: vf.name.name,
        )
        poster_path = context.poster_provider.find_poster_image_with_fallback(
            directory_absolute_path=context.directory.absolute_path,
        )
        return StandaloneFilm(
            id=entry_id_from_path(context.directory.absolute_path),
            name=parse_name(context.directory.name),
            root_relative_path=context.directory.absolute_path,
            root_relative_poster_path=poster_path,
            tags=frozenset(context.lumi_directory_config.tags),
            franchise=context.lumi_directory_config.franchise,
            video_files=video_files,
        )
