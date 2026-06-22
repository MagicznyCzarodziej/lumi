"""Display aspect ratio modes for video playback."""

from __future__ import annotations

from enum import Enum


class VideoAspectMode(str, Enum):
    AUTO = "auto"
    WIDE_16_9 = "16:9"
    CLASSIC_4_3 = "4:3"
    ULTRAWIDE_21_9 = "21:9"
    CINEMA_2_35 = "2.35:1"
    FILL = "fill"


VIDEO_ASPECT_MODES: tuple[VideoAspectMode, ...] = (
    VideoAspectMode.AUTO,
    VideoAspectMode.WIDE_16_9,
    VideoAspectMode.CLASSIC_4_3,
    VideoAspectMode.ULTRAWIDE_21_9,
    VideoAspectMode.CINEMA_2_35,
    VideoAspectMode.FILL,
)


def video_aspect_label(mode: VideoAspectMode) -> str:
    labels = {
        VideoAspectMode.AUTO: "Auto",
        VideoAspectMode.WIDE_16_9: "16:9",
        VideoAspectMode.CLASSIC_4_3: "4:3",
        VideoAspectMode.ULTRAWIDE_21_9: "21:9",
        VideoAspectMode.CINEMA_2_35: "2.35:1",
        VideoAspectMode.FILL: "Fill screen",
    }
    return labels[mode]


def video_aspect_override_value(mode: VideoAspectMode) -> float | None:
    """Return mpv video-aspect-override value, or None to disable override."""
    ratios = {
        VideoAspectMode.WIDE_16_9: 16 / 9,
        VideoAspectMode.CLASSIC_4_3: 4 / 3,
        VideoAspectMode.ULTRAWIDE_21_9: 21 / 9,
        VideoAspectMode.CINEMA_2_35: 2.35,
    }
    return ratios.get(mode)


def parse_video_aspect_mode(value: object) -> VideoAspectMode | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return VideoAspectMode(value.strip())
    except ValueError:
        return None
