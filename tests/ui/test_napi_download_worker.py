from __future__ import annotations

from pathlib import PurePosixPath
from unittest.mock import MagicMock

from lumi.infrastructure.mock.mock_file_repository import MockFileRepository
from lumi.infrastructure.subtitles.mock_subtitle_provider import MockSubtitleDownloadProvider
from lumi.infrastructure.subtitles.disk_subtitle_cache import DiskSubtitleCache
from lumi.ui.workers.napi_download_worker import NapiDownloadWorker


def test_napi_download_worker_reads_resolved_path(tmp_path) -> None:
    repo = MockFileRepository()
    hint = PurePosixPath("/Movies/Foo/Foo.mkv")
    resolved = PurePosixPath("/media/Movies/Foo/Foo.mkv")
    repo.seed_file(resolved, b"video-bytes-for-hash")

    resolver = MagicMock()
    resolver.resolve_path.return_value = resolved

    cache = DiskSubtitleCache(tmp_path)
    worker = NapiDownloadWorker(
        hint,
        video_reader=repo,
        provider=MockSubtitleDownloadProvider(),
        subtitle_cache=cache,
        language="EN",
        playback_uri_resolver=resolver,
    )
    worker.run()

    resolver.resolve_path.assert_called_once_with(hint)
    assert cache.contains(hint)
