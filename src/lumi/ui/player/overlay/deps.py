"""Dependencies injected into the player overlay from the composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.file_writer import FileWriter
from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.provider import SubtitleDownloadProvider
from lumi.domain.subtitles.saved_state import NapiSavedStateStore


@dataclass(frozen=True)
class OverlayDeps:
    files_lister: FilesLister | None = None
    playback_uri_resolver: PlaybackUriResolver | None = None
    library_root: PurePosixPath | None = None
    video_extensions: frozenset[str] = field(default_factory=frozenset)
    subtitle_extensions: frozenset[str] = field(default_factory=frozenset)
    subtitle_cache: SubtitleCache | None = None
    napi_provider: SubtitleDownloadProvider | None = None
    napi_saved_state: NapiSavedStateStore | None = None
    video_reader: VideoRangeReader | None = None
    file_repository: FileRepository | None = None
    file_writer: FileWriter | None = None
    napi_enabled: bool = False
    napi_language: str = "ENG"
    on_close: Callable[[], None] | None = None

    @property
    def napi_available(self) -> bool:
        return self.napi_enabled and self.napi_provider is not None and self.subtitle_cache is not None
