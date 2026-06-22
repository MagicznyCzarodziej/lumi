from __future__ import annotations

from unittest.mock import MagicMock

from lumi.domain.subtitles.content_hash import subtitle_content_hash
from lumi.ui.player.controller.controller import MpvController


def test_find_subtitle_track_for_content_matches_known_hash() -> None:
    controller = MpvController(MagicMock(return_value=None))
    data = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"
    controller._subtitle_content_hashes[3] = subtitle_content_hash(data)
    controller._tracks = lambda: [{"id": 3, "type": "sub"}]  # type: ignore[method-assign]

    assert controller.find_subtitle_track_for_content(data, read_uri=lambda _uri: None) == 3
    assert controller.find_subtitle_track_for_content(b"other", read_uri=lambda _uri: None) is None


def test_find_subtitle_track_for_content_reads_external_uri() -> None:
    controller = MpvController(MagicMock(return_value=None))
    controller._tracks = lambda: [  # type: ignore[method-assign]
        {
            "id": 5,
            "type": "sub",
            "external-filename": "file:///tmp/Movie.srt",
        }
    ]
    data = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"

    def read_uri(uri: str) -> bytes | None:
        assert uri == "file:///tmp/Movie.srt"
        return data

    assert controller.find_subtitle_track_for_content(data, read_uri=read_uri) == 5
