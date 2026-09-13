"""Library root screen — poster, filters, A–Z, tag sidebar drawer."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QVBoxLayout

from lumi.domain.library.models import LibraryEntry
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import Destination
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.screens.library.controller import (
    active_letter_for_row,
    build_alphabet_symbols,
    build_library_ui_state,
    find_entry_index_for_letter,
    EntriesFilter,
    LibraryUiState,
)
from lumi.ui.screens.library.library_layout import LibraryLayout


class LibraryScreen(NavigableScreen):
    def __init__(
        self,
        router: Router,
        *,
        on_rebuild_library: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._router = router
        self._on_rebuild_library = on_rebuild_library
        self._context: ScreenContext | None = None
        self._all_entries: list[LibraryEntry] = []
        self._entries_filter = EntriesFilter.ALL
        self._tag_filter: str | None = None
        self._search_query = ""
        self._ui_state = LibraryUiState(entries=[], tags=[], is_loading=True)
        self._previous_alphabet_letter: str | None = None
        self._is_loading = True
        self._rebuild_in_progress = False

        self._layout = LibraryLayout()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._layout)

        self._layout.top_bar.filter_changed.connect(self._on_filter_changed)
        self._layout.top_bar.search_changed.connect(self._on_search_changed)
        self._layout.top_bar.navigate_down.connect(self._focus_current_entry)
        self._layout.sidebar.tag_filter_changed.connect(self._on_tag_filter_changed)
        self._layout.sidebar.rebuild_requested.connect(self._request_rebuild)
        self._layout.sidebar.navigate_to_entries.connect(self._leave_sidebar_to_entries)
        self._layout.alphabet.letter_activated.connect(self._on_letter_activated)
        self._layout.alphabet.exit_to_entries.connect(self._focus_current_entry)
        self._layout.entries.focus_left_requested.connect(self._focus_active_letter)
        self._layout.entries.focus_right_requested.connect(self._open_sidebar)
        self._layout.entries.focus_up_requested.connect(self._layout.top_bar.focus_first_filter)
        self._layout.entries.type_to_search.connect(self._on_type_to_search)
        self._layout.entries.clear_search_requested.connect(self._on_clear_search_requested)
        self._layout.entries.backspace_search_requested.connect(
            self._layout.top_bar.remove_last_search_character
        )
        self._layout.entries.currentRowChanged.connect(self._on_entry_row_changed)

        self.set_loading()

    def bind_poster_loader(self, loader: PosterLoader) -> None:
        self._layout.poster.bind_loader(loader)

    def bind(self, destination: Destination, context: ScreenContext) -> None:
        del destination
        self._context = context
        self._refresh_entries_from_repository()

    def set_loading(self) -> None:
        self._is_loading = True
        self._rebuild_in_progress = False
        self._search_query = ""
        self._layout.top_bar.clear_search()
        self._layout.status_bar.set_progress(None)
        self._layout.entries.set_entries([])
        self._layout.empty_label.hide()
        self._layout.entries.show()
        self._layout.poster.set_poster_path(None, immediate=True)
        self._layout.poster_skeleton.start()
        self._layout.entries_skeleton.start()
        self._layout.sync_skeleton_geometry()

    def has_library(self) -> bool:
        return bool(self._all_entries)

    def set_rebuilding(self) -> None:
        """Keep the current library visible while a rebuild runs in the background."""
        self._rebuild_in_progress = True
        self._layout.status_bar.set_progress((0, 0, ""))

    def clear_rebuild_progress(self) -> None:
        self._rebuild_in_progress = False
        self._layout.status_bar.set_progress(None)

    def set_ready(self, context: ScreenContext) -> None:
        self._context = context
        self._is_loading = False
        self._rebuild_in_progress = False
        self._layout.status_bar.set_progress(None)
        self._layout.poster_skeleton.stop()
        self._layout.entries_skeleton.stop()
        self._refresh_entries_from_repository()
        self.focus_default()

    def focus_default(self) -> None:
        if self._is_loading:
            self._layout.top_bar.focus_first_filter()
            return
        if self._ui_state.entries:
            self._focus_current_entry()
        else:
            self._layout.top_bar.focus_first_filter()

    def set_error(self, message: str) -> None:
        self._is_loading = False
        self._rebuild_in_progress = False
        self._layout.status_bar.set_progress(None)
        self._layout.poster_skeleton.stop()
        self._layout.entries_skeleton.stop()
        self._layout.entries.hide()
        self._layout.empty_label.setText(message)
        self._layout.empty_label.show()
        self._layout.poster.set_poster_path(None, immediate=True)

    def set_loading_progress(self, completed: int, total: int, directory_name: str) -> None:
        if not self._rebuild_in_progress:
            return
        self._layout.status_bar.set_progress((completed, total, directory_name))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout.sync_skeleton_geometry()
        self._layout.position_status_bar()
        self._layout.position_sidebar_drawer()

    def _request_rebuild(self) -> None:
        if self._on_rebuild_library is not None:
            self._on_rebuild_library()

    def _refresh_entries_from_repository(self) -> None:
        if self._context is None:
            return
        self._all_entries = self._context.library_repository.get_top_level_entries()
        self._rebuild_ui_state(is_loading=False)

    def _rebuild_ui_state(self, *, is_loading: bool) -> None:
        if self._context is None:
            return

        self._ui_state = build_library_ui_state(
            self._all_entries,
            entries_filter=self._entries_filter,
            tag_filter=self._tag_filter,
            search_query=self._search_query,
            router=self._router,
            video_player=self._context.video_player,
            is_loading=is_loading,
        )
        self._apply_ui_state()

    def _apply_ui_state(self) -> None:
        entries_had_focus = self._entries_has_focus()
        alphabet_had_focus = self._alphabet_has_focus()
        search_had_focus = self._layout.top_bar.search_has_focus()

        self._layout.sidebar.set_active_tag(self._tag_filter)
        self._layout.sidebar.set_tags(self._ui_state.tags)
        self._layout.top_bar.set_active_filter(self._entries_filter)

        symbols = build_alphabet_symbols(self._ui_state.entries)
        self._layout.alphabet.set_symbols(symbols)
        self._layout.entries.set_entries(self._ui_state.entries, preserve_focus=True)

        row = self._layout.entries.focused_row()
        letter = active_letter_for_row(self._ui_state.entries, row)
        self._layout.alphabet.set_active_letter(letter)
        if not self._alphabet_has_focus():
            self._layout.alphabet.scroll_to_letter(letter)
        self._previous_alphabet_letter = letter

        if self._ui_state.entries:
            self._layout.empty_label.hide()
            self._layout.entries.show()
            focus_row = min(row, len(self._ui_state.entries) - 1)
            self._layout.entries.scroll_to_row(focus_row)
            model = self._ui_state.entries[focus_row]
            self._layout.poster.set_poster_path(model.poster_path, immediate=True)
        else:
            if self._search_query.strip():
                self._layout.empty_label.setText("No entries match your search.")
                self._layout.empty_label.show()
                self._layout.entries.show()
            else:
                self._layout.entries.hide()
                if self._all_entries:
                    self._layout.empty_label.setText("No entries match the current filters.")
                else:
                    self._layout.empty_label.setText("Library is empty.")
                self._layout.empty_label.show()
            self._layout.poster.set_poster_path(None, immediate=True)

        if self._layout.sidebar.is_open():
            QTimer.singleShot(0, self._layout.sidebar.restore_menu_focus)
            return

        if entries_had_focus:
            if self._ui_state.entries:
                self._focus_current_entry()
            elif self._search_query.strip():
                self._layout.entries.setFocus(Qt.FocusReason.OtherFocusReason)
        elif alphabet_had_focus:
            self._focus_active_letter()
        elif search_had_focus:
            self._layout.top_bar.focus_search()

    def _on_filter_changed(self, filter_value: EntriesFilter) -> None:
        self._entries_filter = filter_value
        self._rebuild_ui_state(is_loading=False)

    def _on_tag_filter_changed(self, tag: object) -> None:
        self._tag_filter = tag if isinstance(tag, str) else None
        self._rebuild_ui_state(is_loading=False)

    def _on_search_changed(self, query: str) -> None:
        self._search_query = query
        self._rebuild_ui_state(is_loading=False)

    def _on_type_to_search(self, char: str) -> None:
        self._layout.top_bar.append_search_character(char)

    def _on_clear_search_requested(self) -> None:
        if not self._search_query:
            return
        self._layout.top_bar.clear_search()
        self._search_query = ""
        self._rebuild_ui_state(is_loading=False)

    def _on_entry_row_changed(self, row: int) -> None:
        letter = active_letter_for_row(self._ui_state.entries, row)
        self._layout.alphabet.set_active_letter(letter)
        if (
            self._entries_has_focus()
            and not self._alphabet_has_focus()
            and letter != self._previous_alphabet_letter
        ):
            self._layout.alphabet.scroll_to_letter(letter)
        self._previous_alphabet_letter = letter
        if 0 <= row < len(self._ui_state.entries):
            model = self._ui_state.entries[row]
            immediate = not self._layout.entries.consume_defer_poster_update()
            self._layout.poster.set_poster_path(model.poster_path, immediate=immediate)

    def _on_letter_activated(self, letter: str) -> None:
        index = find_entry_index_for_letter(self._ui_state.entries, letter)
        self._layout.entries.scroll_to_row(index)
        self._layout.entries.setFocus(Qt.FocusReason.OtherFocusReason)

    def _focus_current_entry(self) -> None:
        self._layout.entries.scroll_to_row(self._layout.entries.focused_row())
        self._layout.entries.setFocus(Qt.FocusReason.OtherFocusReason)

    def _focus_active_letter(self) -> None:
        row = self._layout.entries.focused_row()
        letter = active_letter_for_row(self._ui_state.entries, row)
        index = self._layout.alphabet.index_for_letter(letter)
        if index >= 0:
            self._layout.alphabet.scroll_to_row(index)
        self._previous_alphabet_letter = letter
        self._layout.alphabet.setFocus(Qt.FocusReason.OtherFocusReason)

    def _open_sidebar(self) -> None:
        self._layout.sidebar.focus_first_item()

    def _leave_sidebar_to_entries(self) -> None:
        self._layout.sidebar.close_drawer()
        self._focus_current_entry()

    def _entries_has_focus(self) -> bool:
        focus = QApplication.focusWidget()
        entries = self._layout.entries
        return focus is not None and (focus is entries or entries.isAncestorOf(focus))

    def _alphabet_has_focus(self) -> bool:
        focus = QApplication.focusWidget()
        alphabet = self._layout.alphabet
        return focus is not None and (focus is alphabet or alphabet.isAncestorOf(focus))
