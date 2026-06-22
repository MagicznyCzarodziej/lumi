from lumi.domain.subtitles.content_hash import normalize_subtitle_bytes, subtitle_content_hash


def test_subtitle_content_hash_ignores_line_endings() -> None:
    left = b"1\r\n00:00:01,000 --> 00:00:02,000\r\nHello\r\n"
    right = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"
    assert subtitle_content_hash(left) == subtitle_content_hash(right)


def test_normalize_subtitle_bytes_strips_trailing_spaces() -> None:
    assert normalize_subtitle_bytes(b"Hello  \nWorld\t") == b"Hello\nWorld"
