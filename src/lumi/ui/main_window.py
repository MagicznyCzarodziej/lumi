"""Main application window."""

from __future__ import annotations

from pathlib import PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence, QResizeEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from lumi.ui.components.keyboard_helpers import is_back_key
from lumi.config.settings import Settings
from lumi.container import Container
from lumi.domain.video_player import VideoPlayer
from lumi.infrastructure.mock.mock_video_player import MockVideoPlayer
from lumi.ui.context import ScreenContext
from lumi.ui.navigation.destinations import (
    LIBRARY,
    EpisodesGroupDestination,
    FilmSeriesDestination,
    LibraryDestination,
    MediaGroupingDestination,
    MediaGroupingEpisodesGroupDestination,
    SeriesDestination,
)
from lumi.ui.navigation.navigable_screen import NavigableScreen
from lumi.ui.navigation.router import Router
from lumi.ui.poster_loader import PosterLoader
from lumi.ui.safe_video_player import SafeVideoPlayer
from lumi.ui.screens.list_with_poster_screen import ListWithPosterScreen
from lumi.ui.screens.episodes.screen import EpisodesScreen
from lumi.ui.screens.film_series.screen import FilmSeriesScreen
from lumi.ui.screens.library.screen import LibraryScreen
from lumi.ui.screens.media_grouping.screen import MediaGroupingScreen
from lumi.ui.screens.media_grouping_episodes.screen import MediaGroupingEpisodesGroupScreen
from lumi.ui.screens.series.screen import SeriesScreen
from lumi.ui.workers.library_init_worker import LibraryInitWorker
from lumi.ui.theme.scale import scaled


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings,
        container: Container,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._container = container
        self._init_worker: LibraryInitWorker | None = None

        self.setWindowTitle("Lumi")
        self.setMinimumSize(scaled(1280), scaled(720))

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._player_host = None
        playback: VideoPlayer
        if settings.mode == "mock":
            playback = MockVideoPlayer()
        else:
            from lumi.ui.embedded_video_player import EmbeddedVideoPlayer
            from lumi.ui.player.host import PlayerHost
            from lumi.infrastructure.power import create_sleep_inhibitor

            self._player_host = PlayerHost(
                self,
                files_lister=container.files_lister,
                playback_uri_resolver=container.playback_uri_resolver,
                library_root=PurePosixPath(settings.library_root),
                video_extensions={
                    ext.lstrip(".").lower() for ext in settings.video_extensions
                },
                subtitle_extensions={
                    ext.lstrip(".").lower() for ext in settings.subtitle_extensions
                },
                subtitle_cache=container.subtitle_cache,
                napi_provider=container.napi_provider,
                napi_saved_state=container.napi_saved_state,
                video_reader=container.smb_file_repository,
                file_repository=container.file_repository,
                file_writer=container.smb_file_repository,
                napi_enabled=settings.napiprojekt.enabled,
                napi_language=settings.napiprojekt.language,
                sleep_inhibitor=create_sleep_inhibitor(),
                library_repository=container.library_repository,
            )
            self._player_host.hide()
            playback = EmbeddedVideoPlayer(container.playback_uri_resolver, self._player_host)
        self._screen_context = ScreenContext(
            library_repository=container.library_repository,
            video_player=SafeVideoPlayer(playback, self._show_playback_error),
        )

        self._router = Router(self._stack, self._screen_context)
        self._poster_loader = PosterLoader(
            container.poster_provider,
            container.poster_cache,
            parent=self,
        )
        self._library_screen = LibraryScreen(
            self._router,
            on_rebuild_library=self._rebuild_library,
        )
        self._library_screen.bind_poster_loader(self._poster_loader)
        self._register_screens()

        self._register_actions()

        self._router.start(LIBRARY)
        self._library_screen.set_loading()
        self._start_library_load()

    def _register_screens(self) -> None:
        loader = self._poster_loader
        self._router.register(LibraryDestination, lambda: self._library_screen)
        self._router.register(SeriesDestination, lambda: SeriesScreen(self._router, poster_loader=loader))
        self._router.register(EpisodesGroupDestination, lambda: EpisodesScreen(poster_loader=loader))
        self._router.register(FilmSeriesDestination, lambda: FilmSeriesScreen(poster_loader=loader))
        self._router.register(MediaGroupingDestination, lambda: MediaGroupingScreen(self._router, poster_loader=loader))
        self._router.register(
            MediaGroupingEpisodesGroupDestination,
            lambda: MediaGroupingEpisodesGroupScreen(poster_loader=loader),
        )

    def _register_actions(self) -> None:
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        quit_action.triggered.connect(self._quit_application)
        self.addAction(quit_action)

        rebuild_action = QAction("Rebuild library", self)
        rebuild_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        rebuild_action.triggered.connect(self._rebuild_library)
        self.addAction(rebuild_action)

    def _start_library_load(self, *, ignore_cache: bool = False) -> None:
        worker = self._init_worker
        if worker is not None:
            try:
                if worker.isRunning():
                    return
            except RuntimeError:
                self._init_worker = None

        root = PurePosixPath(self._settings.library_root)
        if ignore_cache and self._library_screen.has_library():
            self._library_screen.set_rebuilding()
        else:
            self._library_screen.set_loading()

        worker = LibraryInitWorker(
            self._container.library_repository,
            root,
            ignore_cache=ignore_cache,
            parent=self,
        )
        worker.finished_ok.connect(self._on_library_loaded)
        worker.failed.connect(self._on_library_failed)
        worker.progress.connect(self._on_library_progress)
        worker.cache_warning.connect(self._on_cache_warning)
        worker.finished.connect(self._on_init_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._init_worker = worker
        worker.start()

    def _on_init_worker_finished(self) -> None:
        self._init_worker = None

    def _rebuild_library(self) -> None:
        self._start_library_load(ignore_cache=True)

    def _on_library_loaded(self) -> None:
        self._router.reset_to(LIBRARY)
        self._library_screen.set_ready(self._screen_context)

    def _on_library_failed(self, message: str) -> None:
        if self._library_screen.has_library():
            self._library_screen.clear_rebuild_progress()
            QMessageBox.warning(self, "Library rebuild failed", message)
            return
        self._router.reset_to(LIBRARY)
        self._library_screen.set_error(message)

    def _on_library_progress(self, completed: int, total: int, directory_name: str) -> None:
        self._library_screen.set_loading_progress(completed, total, directory_name)

    def _on_cache_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Library cache", message)

    def _show_playback_error(self, message: str) -> None:
        QMessageBox.warning(self, "Playback failed", message)

    def restore_screen_focus(self) -> None:
        screen = self._stack.currentWidget()
        if isinstance(screen, NavigableScreen):
            screen.focus_default()

    def focus_playback_path(self, path: PurePosixPath) -> bool:
        screen = self._stack.currentWidget()
        if isinstance(screen, ListWithPosterScreen):
            return screen.focus_playback_path(path)
        return False

    def _sync_player_host_geometry(self) -> None:
        if self._player_host is not None:
            self._player_host.setGeometry(self.rect())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_player_host_geometry()

    def _quit_application(self) -> None:
        from PySide6.QtWidgets import QApplication

        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _stop_background_workers(self) -> None:
        worker = self._init_worker
        if worker is None:
            return
        try:
            if not worker.isRunning():
                return
        except RuntimeError:
            self._init_worker = None
            return
        worker.requestInterruption()
        if not worker.wait(3000):
            worker.terminate()
            worker.wait(1000)

    def closeEvent(self, event) -> None:
        self._stop_background_workers()
        if self._player_host is not None:
            self._player_host.shutdown()
        event.accept()
        super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if is_back_key(event.key()):
            if self._player_host is not None and self._player_host.is_playing():
                self._player_host.close_player()
                event.accept()
                return
            if self._router.pop():
                event.accept()
                return
        super().keyPressEvent(event)

