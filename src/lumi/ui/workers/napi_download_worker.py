"""Background NapiProjekt subtitle download worker."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from lumi.domain.filesystem.file_repository import FileRepository
from lumi.domain.filesystem.video_range_reader import VideoRangeReader
from lumi.domain.playback import PlaybackUriResolver
from lumi.domain.subtitles.cache import SubtitleCache
from lumi.domain.subtitles.napi_hash import calc_napi_hash
from lumi.domain.subtitles.provider import SubtitleDownloadError, SubtitleDownloadProvider
from lumi.infrastructure.subtitles.hash_reader import read_napi_hash_bytes


class NapiDownloadWorker(QRunnable):
    """Hashes the video from SMB, downloads subtitles, and writes the local cache."""

    def __init__(
        self,
        video_path: PurePosixPath,
        *,
        video_reader: VideoRangeReader,
        provider: SubtitleDownloadProvider,
        subtitle_cache: SubtitleCache,
        language: str,
        playback_uri_resolver: PlaybackUriResolver | None = None,
        stream_uri: str | None = None,
        resolved_video_path: PurePosixPath | None = None,
        file_repository: FileRepository | None = None,
    ) -> None:
        super().__init__()
        self.video_path = video_path
        self._video_reader = video_reader
        self._provider = provider
        self._subtitle_cache = subtitle_cache
        self._language = language
        self._playback_uri_resolver = playback_uri_resolver
        self._stream_uri = stream_uri
        self._resolved_video_path = resolved_video_path
        self._file_repository = file_repository
        self.signals = _NapiDownloadSignals()

    @Slot()
    def run(self) -> None:
        path = self.video_path
        try:
            if self._subtitle_cache.contains(path):
                local_path = self._subtitle_cache.local_path(path)
                if local_path is not None:
                    self.signals.finished.emit(path, local_path, True)
                    return

            hash_bytes = read_napi_hash_bytes(
                video_path=path,
                video_reader=self._video_reader,
                playback_uri_resolver=self._playback_uri_resolver,
                stream_uri=self._stream_uri,
                resolved_video_path=self._resolved_video_path,
                file_repository=self._file_repository,
            )
            movie_hash = calc_napi_hash(hash_bytes)
            srt_bytes = self._provider.download_by_hash(movie_hash, language=self._language)
            local_path = self._subtitle_cache.write(path, srt_bytes)
            self.signals.finished.emit(path, local_path, False)
        except SubtitleDownloadError as exc:
            self.signals.failed.emit(path, str(exc))
        except Exception as exc:
            self.signals.failed.emit(path, str(exc))


class _NapiDownloadSignals(QObject):
    finished = Signal(object, object, bool)
    failed = Signal(object, str)
