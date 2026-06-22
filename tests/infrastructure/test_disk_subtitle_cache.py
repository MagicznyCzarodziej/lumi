from __future__ import annotations

from pathlib import PurePosixPath

from lumi.infrastructure.subtitles.disk_subtitle_cache import DiskSubtitleCache


def test_disk_subtitle_cache_round_trip(tmp_path) -> None:
    cache = DiskSubtitleCache(tmp_path)
    video_path = PurePosixPath("/Movies/Foo/Foo.mkv")
    data = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"

    assert not cache.contains(video_path)
    written = cache.write(video_path, data)
    assert written.is_file()
    assert cache.contains(video_path)
    assert cache.read(video_path) == data
    assert cache.local_path(video_path) == written

    cache.delete(video_path)
    assert not cache.contains(video_path)
    assert cache.read(video_path) is None
