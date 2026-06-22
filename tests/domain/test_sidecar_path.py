from __future__ import annotations

from pathlib import PurePosixPath

from lumi.domain.subtitles.sidecar_path import subtitle_sidecar_path


def test_subtitle_sidecar_path_uses_video_stem() -> None:
    assert subtitle_sidecar_path(PurePosixPath("/Movies/Foo/Foo.mkv")) == PurePosixPath(
        "/Movies/Foo/Foo.srt"
    )
