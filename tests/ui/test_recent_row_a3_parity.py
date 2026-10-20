"""Observable A3 metrics for Recently watched play rows (prototype parity gate)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QStackedWidget, QVBoxLayout, QWidget

from lumi.config.settings import Settings
from lumi.container import build_container
from lumi.domain.recent_watch import RecentWatchRecord
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.components.recent_watch_header import RecentWatchHeader
from lumi.ui.components.recent_watch_list import RecentWatchList
from lumi.ui.components.recent_watch_row import RecentWatchRow
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.router import Router
from lumi.ui.screens.recently_watched.controller import build_recently_watched_state
from lumi.ui.theme.fonts import apply_app_fonts
from lumi.ui.theme.spacing import (
    LIST_ROW_LEFT_INSET,
    LIST_ROW_VERTICAL_INSET,
    LIST_SELECTION_ACCENT_WIDTH,
    RECENT_WATCH_PLAY_BADGE_SIZE,
    RECENT_WATCH_PROGRESS_MAX_WIDTH,
    RECENT_WATCH_ROW_GAP,
    RECENT_WATCH_THUMBNAIL_HEIGHT,
    RECENT_WATCH_THUMBNAIL_WIDTH,
)
from tests.constants import MOCK_LIBRARY_ROOT


class _WH:
    def __init__(self, records: list[RecentWatchRecord]) -> None:
        self._records = records

    def recent_entries(self) -> list[RecentWatchRecord]:
        return self._records


def _panel_with_rows(qtbot) -> tuple[QWidget, RecentWatchList]:
    QApplication.instance() or QApplication([])
    apply_app_fonts(QApplication.instance())
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT, ignore_cache=True)
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Band of Brothers/Season 1/S01E02.mkv"),
            position=240.0,
            duration=3600.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        ),
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 18, 20, 0, tzinfo=UTC),
        ),
    ]
    router = Router(
        QStackedWidget(),
        ScreenContext(container.library_repository, MockVideoPlayer(), _WH(records)),
    )
    state = build_recently_watched_state(
        records,
        container.library_repository.get_top_level_entries(),
        router,
        MockVideoPlayer(),
    )
    assert len(state.rows) == 2

    panel = QWidget()
    panel.setFixedSize(820, 720)
    panel.setStyleSheet("background:#07080F;")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 24, 24, 24)
    layout.setSpacing(18)
    rows = RecentWatchList()
    rows.setFixedWidth(796)
    rows.set_rows(state.rows)
    rows.setFocus(Qt.FocusReason.OtherFocusReason)
    layout.addWidget(RecentWatchHeader())
    layout.addWidget(rows, stretch=1)
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)
    return panel, rows


def _render_thumbnail_image(thumbnail) -> "QImage":
    from PySide6.QtGui import QImage

    dpr = thumbnail.devicePixelRatioF()
    pix = QPixmap(int(thumbnail.width() * dpr), int(thumbnail.height() * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    thumbnail.render(pix)
    return pix.toImage()


def _thumb_has_bright_glyph(thumb_img, *, dpr: float) -> bool:
    cx = thumb_img.width() // 2
    cy = thumb_img.height() // 2
    half = max(8, int(RECENT_WATCH_PLAY_BADGE_SIZE * dpr) // 2)
    peak = 0
    bright = 0
    for dy in range(-half, half):
        for dx in range(-half, half):
            c = thumb_img.pixelColor(cx + dx, cy + dy)
            channel = max(c.red(), c.green(), c.blue())
            peak = max(peak, channel)
            if channel > 200 and c.alpha() > 200:
                bright += 1
    return peak >= 230 and bright >= 15


def test_recent_play_row_a3_geometry_and_play_badge(qtbot) -> None:
    panel, rows = _panel_with_rows(qtbot)
    selected = rows.current_row_widget()
    assert selected is not None
    assert selected.play_badge_visible
    assert selected.thumbnail_size == QSize(
        RECENT_WATCH_THUMBNAIL_WIDTH,
        RECENT_WATCH_THUMBNAIL_HEIGHT,
    )
    assert selected.height() == RECENT_WATCH_THUMBNAIL_HEIGHT + 2 * LIST_ROW_VERTICAL_INSET

    progress = selected.findChild(QProgressBar, "progress")
    assert progress is not None
    assert progress.maximumWidth() == RECENT_WATCH_PROGRESS_MAX_WIDTH

    playable = selected.findChild(QLabel, "playableName")
    body = selected.findChild(QWidget, "body")
    assert playable is not None and body is not None
    assert playable.mapTo(body, playable.rect().topLeft()).y() == 0

    gap = selected._body.geometry().left() - selected._thumbnail.geometry().right()  # noqa: SLF001
    assert abs(gap - RECENT_WATCH_ROW_GAP) <= 1

    show = selected.findChild(QLabel, "showName")
    assert show is not None and show.isVisible()


def test_unselected_recent_row_hides_play_badge_but_keeps_progress(qtbot) -> None:
    panel, rows = _panel_with_rows(qtbot)
    rows.setCurrentRow(1)
    first_item = rows.item(0)
    assert first_item is not None
    first_row = rows.itemWidget(first_item)
    assert isinstance(first_row, RecentWatchRow)
    assert not first_row.play_badge_visible
    when = first_row.findChild(QLabel, "when")
    assert when is not None and when.text().endswith("%")
    second_row = rows.current_row_widget()
    assert second_row is not None and second_row.play_badge_visible


def test_poster_play_badge_paints_on_selected_row(qtbot) -> None:
    QApplication.instance() or QApplication([])
    apply_app_fonts(QApplication.instance())
    container = build_container(Settings(mode="mock"))
    container.library_repository.initialize(MOCK_LIBRARY_ROOT, ignore_cache=True)
    records = [
        RecentWatchRecord(
            library_path=PurePosixPath("Alien/Alien.mkv"),
            position=120.0,
            duration=7200.0,
            watched_at=datetime(2026, 10, 19, 20, 0, tzinfo=UTC),
        )
    ]
    router = Router(
        QStackedWidget(),
        ScreenContext(container.library_repository, MockVideoPlayer(), _WH(records)),
    )
    state = build_recently_watched_state(
        records,
        container.library_repository.get_top_level_entries(),
        router,
        MockVideoPlayer(),
    )
    row = RecentWatchRow(state.rows[0])
    qtbot.addWidget(row)
    row.setFixedWidth(720)
    row.set_row_selected(True)
    row.show()
    qtbot.waitExposed(row)

    thumb_img = _render_thumbnail_image(row._thumbnail)  # noqa: SLF001
    assert _thumb_has_bright_glyph(thumb_img, dpr=thumb_img.devicePixelRatio())
