"""Default file extensions."""

DEFAULT_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".flv", ".ts", ".wmv", ".mpg", ".mpeg", ".vob"}
)
DEFAULT_POSTER_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp"})
DEFAULT_SUBTITLE_EXTENSIONS: frozenset[str] = frozenset({".srt", ".ass", ".ssa", ".vtt", ".sub", ".txt"})
DEFAULT_POSTER_FILE_NAME = "poster"
