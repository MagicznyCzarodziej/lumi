"""Tests for video aspect ratio modes."""

from __future__ import annotations

from lumi.domain.video_aspect import (
    VIDEO_ASPECT_MODES,
    VideoAspectMode,
    parse_video_aspect_mode,
    video_aspect_label,
    video_aspect_override_value,
)


def test_video_aspect_override_values() -> None:
    assert video_aspect_override_value(VideoAspectMode.AUTO) is None
    assert video_aspect_override_value(VideoAspectMode.FILL) is None
    assert video_aspect_override_value(VideoAspectMode.WIDE_16_9) == 16 / 9
    assert video_aspect_override_value(VideoAspectMode.CLASSIC_4_3) == 4 / 3


def test_video_aspect_modes_have_labels() -> None:
    for mode in VIDEO_ASPECT_MODES:
        assert video_aspect_label(mode)


def test_parse_video_aspect_mode() -> None:
    assert parse_video_aspect_mode("16:9") == VideoAspectMode.WIDE_16_9
    assert parse_video_aspect_mode("fill") == VideoAspectMode.FILL
    assert parse_video_aspect_mode("invalid") is None
