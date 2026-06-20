"""Shared 37/63 poster + list layout."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from lumi.ui.components.entries_list import EntriesList
from lumi.ui.components.list_entry import ListEntryUiModel, NameDisplayStrategy
from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.components.skeleton_overlay import SkeletonOverlay
from lumi.ui.layouts.header import Header
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.theme.spacing import LIST_CONTENT_MARGINS, LIST_LAYOUT_STRETCH, POSTER_LAYOUT_STRETCH
from lumi.ui.theme.styles import apply_widget_stylesheet


@dataclass
class ListWithPosterViewState:
    poster_path: PurePosixPath | None = None
    breadcrumbs: str = ""
    title: str = ""
    subtitle: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    entries: list[ListEntryUiModel] = field(default_factory=list)
    is_loading: bool = False


class ListWithPosterLayout(QWidget):
    def __init__(
        self,
        *,
        name_display_strategy: NameDisplayStrategy = NameDisplayStrategy.REGULAR,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ListWithPosterLayout")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))

        self._poster = PosterWidget()
        self._poster_skeleton = SkeletonOverlay(parent=self._poster)
        self._header = Header()
        self._entries = EntriesList(name_display_strategy=name_display_strategy)
        self._entries_skeleton = SkeletonOverlay(compact=True, parent=self._entries)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(*LIST_CONTENT_MARGINS)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._header)
        content_layout.addWidget(self._entries, stretch=1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(content, stretch=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._poster, stretch=POSTER_LAYOUT_STRETCH)
        layout.addWidget(right, stretch=LIST_LAYOUT_STRETCH)

        self._entries.currentRowChanged.connect(self._on_entry_row_changed)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_skeleton_geometry()

    def _sync_skeleton_geometry(self) -> None:
        self._poster_skeleton.setGeometry(self._poster.rect())
        self._entries_skeleton.setGeometry(self._entries.rect())

    def set_poster_loader(self, loader: PosterLoader) -> None:
        self._poster.bind_loader(loader)

    def _on_entry_row_changed(self, row: int) -> None:
        if row < 0 or row >= self._entries.count():
            return
        item = self._entries.item(row)
        if item is None:
            return
        model = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(model, ListEntryUiModel) and model.poster_path is not None:
            self._poster.set_poster_path(model.poster_path)

    @property
    def entries_list(self) -> EntriesList:
        return self._entries

    @property
    def poster_widget(self) -> PosterWidget:
        return self._poster

    def apply_state(self, state: ListWithPosterViewState | None) -> None:
        if state is None or state.is_loading:
            self._poster.set_poster_path(None, immediate=True)
            self._header.set_content(breadcrumbs="", title="", tags=frozenset())
            self._entries.set_entries([])
            self._poster_skeleton.start()
            self._entries_skeleton.start()
            self._sync_skeleton_geometry()
            return

        self._poster_skeleton.stop()
        self._entries_skeleton.stop()

        self._poster.set_poster_path(state.poster_path, immediate=True)
        self._header.set_content(
            breadcrumbs=state.breadcrumbs,
            title=state.title,
            subtitle=state.subtitle,
            tags=state.tags,
        )
        self._entries.set_entries(state.entries)
