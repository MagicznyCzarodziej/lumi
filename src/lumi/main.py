"""QApplication entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from lumi.config.settings import Settings, get_settings
from lumi.container import build_container
from lumi.ui.theme import apply_global_theme

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _configure_opengl() -> None:
    """libmpv render API requires OpenGL 3.2+ core on macOS (videotoolbox)."""
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setVersion(3, 2)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    QSurfaceFormat.setDefaultFormat(fmt)


def _present_main_window(window, app: QApplication, settings: Settings) -> None:
    screens = app.screens()
    screen_index = settings.window.screen_index
    if 0 <= screen_index < len(screens):
        screen = screens[screen_index]
        window.setScreen(screen)
        if settings.window.fullscreen:
            window.setGeometry(screen.availableGeometry())
            window.showFullScreen()
            return
        window.setGeometry(screen.availableGeometry())
        window.show()
        return
    if settings.window.fullscreen:
        window.showFullScreen()
    else:
        window.show()


def main() -> None:
    settings = get_settings()
    logger.info("Starting Lumi (mode=%s)", settings.mode)

    _configure_opengl()
    container = build_container(settings)

    app = QApplication(sys.argv)
    app.setApplicationName("Lumi")
    apply_global_theme(app)
    app.aboutToQuit.connect(container.shutdown)

    # Import after settings so mock mode never loads libmpv.
    from lumi.ui.main_window import MainWindow

    window = MainWindow(settings=settings, container=container)
    _present_main_window(window, app, settings)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
