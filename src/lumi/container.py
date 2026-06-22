"""Dependency injection wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from lumi.config.settings import Settings
from lumi.config.validation import validate_settings_for_mode
from lumi.config.smb_config import SmbConfig
from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.files_lister import FilesLister
from lumi.domain.library.building.library_builder import LibraryBuilder
from lumi.domain.library.building.library_parser import LibraryParser
from lumi.domain.library.library_cache import LibraryCache
from lumi.domain.library.library_repository import LibraryRepository
from lumi.domain.lumi_directory_config.provider import LumiDirectoryConfigProvider
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.poster.image_file_poster_provider import ImageFilePosterProvider
from lumi.domain.poster.poster_cache import PosterCache
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.provider import SubtitleDownloadProvider
from lumi.domain.subtitles.saved_state import NapiSavedStateStore
from lumi.infrastructure.in_memory_cached_library_repository import InMemoryCachedLibraryRepository
from lumi.infrastructure.library_cache.library_json_cache import LibraryJsonCache
from lumi.infrastructure.mock.mock_file_repository import MockFileRepository
from lumi.infrastructure.mock.mock_library_builder import MockLibraryBuilder
from lumi.infrastructure.mock.mock_lumi_directory_config_provider import MockLumiDirectoryConfigProvider
from lumi.infrastructure.mock.mock_playback_uri import MockPlaybackUriResolver
from lumi.infrastructure.paths import library_cache_path, poster_cache_dir, subtitle_cache_dir
from lumi.infrastructure.poster_cache.disk_poster_cache import DiskPosterCache
from lumi.infrastructure.subtitles.disk_subtitle_cache import DiskSubtitleCache
from lumi.infrastructure.subtitles.mock_subtitle_provider import MockSubtitleDownloadProvider
from lumi.infrastructure.subtitles.napi_client import NapiProjektClient
from lumi.infrastructure.subtitles.napi_saved_state import JsonNapiSavedStateStore
from lumi.infrastructure.smb.smb_config_reader import SmbLumiDirectoryConfigFileReader
from lumi.infrastructure.smb.smb_file_repository import SmbFileRepository
from lumi.infrastructure.smb.smb_library_builder import SmbLibraryBuilder
from lumi.infrastructure.smb.smb_playback_uri import SmbPlaybackUriResolver
from lumi.infrastructure.smb.smb_stream_server import SmbHttpStreamServer


@dataclass
class Container:
    settings: Settings
    file_repository: FileRepository
    files_lister: FilesLister
    lumi_directory_config_provider: LumiDirectoryConfigProvider
    poster_provider: ImageFilePosterProvider
    poster_cache: PosterCache
    library_parser: LibraryParser
    library_cache: LibraryCache
    library_repository: LibraryRepository
    playback_uri_resolver: PlaybackUriResolver
    subtitle_cache: SubtitleCache
    napi_saved_state: NapiSavedStateStore
    napi_provider: SubtitleDownloadProvider
    library_builder: LibraryBuilder | None = None
    smb_file_repository: SmbFileRepository | None = None
    smb_stream_server: SmbHttpStreamServer | None = None

    def shutdown(self) -> None:
        resolver = self.playback_uri_resolver
        if isinstance(resolver, SmbPlaybackUriResolver):
            resolver.shutdown()
        if self.smb_file_repository is not None:
            self.smb_file_repository.disconnect()


def build_container(settings: Settings | None = None) -> Container:
    from lumi.config.settings import get_settings

    settings = settings or get_settings()
    validate_settings_for_mode(settings)
    video_extensions = _video_extensions_set(settings)
    library_cache = LibraryJsonCache(library_cache_path(settings))
    poster_cache: PosterCache = DiskPosterCache(poster_cache_dir(settings))
    subtitle_cache: SubtitleCache = DiskSubtitleCache(subtitle_cache_dir(settings))
    napi_saved_state = JsonNapiSavedStateStore()

    smb_file_repository: SmbFileRepository | None = None
    smb_stream_server: SmbHttpStreamServer | None = None
    library_builder: LibraryBuilder | None = None

    if settings.mode == "mock":
        mock_repo = MockFileRepository()
        file_repository: FileRepository = mock_repo
        files_lister: FilesLister = mock_repo
        lumi_directory_config_provider: LumiDirectoryConfigProvider = MockLumiDirectoryConfigProvider()
        library_builder = MockLibraryBuilder()
        library_repository: LibraryRepository = InMemoryCachedLibraryRepository(library_builder, library_cache)
        playback_uri_resolver: PlaybackUriResolver = MockPlaybackUriResolver()
        napi_provider: SubtitleDownloadProvider = MockSubtitleDownloadProvider()
    else:
        smb_config = SmbConfig.from_settings(settings)
        smb_file_repository = SmbFileRepository(smb_config)
        smb_stream_server = SmbHttpStreamServer(smb_file_repository)
        file_repository = smb_file_repository
        files_lister = smb_file_repository
        lumi_directory_config_provider = SmbLumiDirectoryConfigFileReader(smb_file_repository)
        library_root = PurePosixPath(settings.library_root)
        playback_uri_resolver = SmbPlaybackUriResolver(
            smb_file_repository,
            smb_stream_server,
            library_root,
            video_extensions,
        )
        napi_provider = NapiProjektClient()

    poster_provider = ImageFilePosterProvider(
        file_repository=file_repository,
        files_lister=files_lister,
        poster_file_name=settings.poster_file_name,
        supported_file_extensions=set(settings.poster_extensions),
    )
    library_parser = LibraryParser(
        file_lister=files_lister,
        poster_provider=poster_provider,
        video_extensions=video_extensions,
        lumi_directory_config_provider=lumi_directory_config_provider,
    )

    if settings.mode == "smb":
        assert smb_file_repository is not None
        library_builder = SmbLibraryBuilder(smb_file_repository, library_parser)
        library_repository = InMemoryCachedLibraryRepository(library_builder, library_cache)

    assert library_builder is not None

    return Container(
        settings=settings,
        file_repository=file_repository,
        files_lister=files_lister,
        lumi_directory_config_provider=lumi_directory_config_provider,
        poster_provider=poster_provider,
        poster_cache=poster_cache,
        library_parser=library_parser,
        library_cache=library_cache,
        library_repository=library_repository,
        playback_uri_resolver=playback_uri_resolver,
        subtitle_cache=subtitle_cache,
        napi_saved_state=napi_saved_state,
        napi_provider=napi_provider,
        library_builder=library_builder,
        smb_file_repository=smb_file_repository,
        smb_stream_server=smb_stream_server,
    )


def _video_extensions_set(settings: Settings) -> set[str]:
    return {ext.lstrip(".").lower() for ext in settings.video_extensions}
