from lumi.domain.subtitles.delay import format_sub_delay


def test_format_sub_delay_zero() -> None:
    assert format_sub_delay(0.0) == "In sync"
    assert format_sub_delay(0.02) == "In sync"


def test_format_sub_delay_later() -> None:
    assert format_sub_delay(0.5) == "0.5 s later"


def test_format_sub_delay_earlier() -> None:
    assert format_sub_delay(-1.0) == "1.0 s earlier"
