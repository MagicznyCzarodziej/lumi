"""Shared library root layout widgets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from lumi.ui.components.alphabet_column import AlphabetColumn
from lumi.ui.components.entries_list import EntriesList
from lumi.ui.components.list_entry import NameDisplayStrategy
from lumi.ui.components.poster_widget import PosterWidget
from lumi.ui.components.sidebar import Sidebar
from lumi.ui.components.skeleton_overlay import SkeletonOverlay
from lumi.ui.components.top_bar import TopBar
from lumi.ui.theme.spacing import (
    ALPHABET_WRAPPER_LEFT_MARGIN,
    ALPHABET_WRAPPER_WIDTH,
    LIST_LAYOUT_STRETCH,
    LIST_OUTER_MARGINS,
    POSTER_LAYOUT_STRETCH,
)
from lumi.ui.theme.styles import apply_widget_stylesheet


class LibraryLayout(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LibraryScreen")
        apply_widget_stylesheet(self, Path(__file__).with_name("screen.qss"))

        self.poster = PosterWidget()
        self.poster_skeleton = SkeletonOverlay(parent=self.poster)
        self.alphabet = AlphabetColumn()
        self.top_bar = TopBar()
        self.entries = EntriesList(
            name_display_strategy=NameDisplayStrategy.LIBRARY,
            escape_clears_search=True,
        )
        self.entries_skeleton = SkeletonOverlay(compact=True, parent=self.entries)
        self.sidebar = Sidebar(self)
        self.empty_label = QLabel("No entries match the current filters.")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.poster, stretch=POSTER_LAYOUT_STRETCH)

        list_panel = QWidget()
        list_panel_layout = QHBoxLayout(list_panel)
        list_panel_layout.setContentsMargins(0, 0, 0, 0)
        list_panel_layout.setSpacing(0)

        alphabet_wrapper = QWidget()
        alphabet_wrapper.setFixedWidth(ALPHABET_WRAPPER_WIDTH)
        alphabet_layout = QHBoxLayout(alphabet_wrapper)
        alphabet_layout.setContentsMargins(ALPHABET_WRAPPER_LEFT_MARGIN, 0, 0, 0)
        alphabet_layout.setSpacing(0)
        alphabet_layout.addWidget(self.alphabet, alignment=Qt.AlignmentFlag.AlignVCenter)
        list_panel_layout.addWidget(alphabet_wrapper, alignment=Qt.AlignmentFlag.AlignVCenter)

        entries_panel = QWidget()
        entries_layout = QVBoxLayout(entries_panel)
        entries_layout.setContentsMargins(0, 0, 0, 0)
        entries_layout.setSpacing(0)
        entries_layout.addWidget(self.top_bar)

        entries_outer = QWidget()
        entries_outer_layout = QVBoxLayout(entries_outer)
        entries_outer_layout.setContentsMargins(*LIST_OUTER_MARGINS)
        entries_outer_layout.setSpacing(0)
        entries_outer_layout.addWidget(self.empty_label)
        entries_outer_layout.addWidget(self.entries, stretch=1)
        entries_layout.addWidget(entries_outer, stretch=1)
        list_panel_layout.addWidget(entries_panel, stretch=1)
        content_layout.addWidget(list_panel, stretch=LIST_LAYOUT_STRETCH)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(content)

    def sync_skeleton_geometry(self) -> None:
        self.poster_skeleton.setGeometry(self.poster.rect())
        self.entries_skeleton.setGeometry(self.entries.rect())

    def position_sidebar_drawer(self) -> None:
        self.sidebar.sync_geometry(self.width(), self.height())
        if self.sidebar.is_open():
            self.sidebar.raise_()
