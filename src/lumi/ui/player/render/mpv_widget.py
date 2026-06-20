"""OpenGL mpv render widget (no UI knowledge)."""

from __future__ import annotations

import locale
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QOpenGLContext
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from lumi.infrastructure.player_preferences import load_player_preferences
from lumi.ui.player.platform.mpv_loader import get_mpv

logger = logging.getLogger(__name__)


def _ensure_c_locale() -> None:
    # "C" is the default POSIX locale (dot decimals). mpv expects that; user locales may use comma.
    locale.setlocale(locale.LC_NUMERIC, "C")


def _get_proc_address(_ctx, name: bytes) -> int:
    glctx = QOpenGLContext.currentContext()
    if glctx is None:
        return 0
    address = glctx.getProcAddress(name)
    if address is None:
        return 0
    return int(address)


class MpvWidget(QOpenGLWidget):
    render_update = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        _ensure_c_locale()
        mpv = get_mpv()
        self._ctx = None
        self._pending_path: str | None = None
        self._start_at: float | None = None
        self._proc_addr = mpv.MpvGlGetProcAddressFn(_get_proc_address)
        self.render_update.connect(self.update, Qt.ConnectionType.QueuedConnection)
        self.frameSwapped.connect(self._on_swap, Qt.ConnectionType.DirectConnection)

        saved_volume = load_player_preferences().volume
        self.mpv = mpv.MPV(
            vo="libmpv",
            keep_open="yes",
            idle="yes",
            pause=False,
            osc="no",
            terminal="no",
            sub_auto="fuzzy",
            network_timeout=60,
            cache="yes",
            video_timing_offset=0,
            volume=saved_volume,
            log_handler=self._on_mpv_log,
            loglevel="warn",
        )
        self._updates_enabled = True
        self._bind_mpv_events()

    def _on_mpv_log(self, level: str, prefix: str, text: str) -> None:
        message = text.strip()
        if not message:
            return
        logger.warning("mpv [%s] %s: %s", level, prefix, message)

    def _bind_mpv_events(self) -> None:
        @self.mpv.event_callback("file-loaded")
        def _on_file_loaded(_event) -> None:
            start_at = self._start_at
            self._start_at = None
            if start_at is not None and start_at > 0:
                self.mpv.time_pos = start_at
            self.mpv.pause = False

        @self.mpv.event_callback("end-file")
        def _on_end_file(event) -> None:
            data = event.data
            if data is None:
                return
            if data.reason == data.ERROR and data.error:
                logger.error("mpv playback failed (reason=%s, error=%s)", data.reason, data.error)

    def initializeGL(self):
        if self._ctx is not None:
            return
        mpv = get_mpv()
        self._ctx = mpv.MpvRenderContext(
            self.mpv,
            "opengl",
            opengl_init_params={"get_proc_address": self._proc_addr},
        )
        self._ctx.update_cb = self._on_mpv_update
        self._flush_pending_load()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.update()

    def resizeGL(self, width: int, height: int) -> None:
        del width, height
        self.update()

    def paintGL(self):
        if self._ctx is None:
            return
        ratio = self.devicePixelRatioF()
        w = int(self.width() * ratio)
        h = int(self.height() * ratio)
        fbo = int(self.defaultFramebufferObject())
        self._ctx.render(
            flip_y=True,
            opengl_fbo={"w": w, "h": h, "fbo": fbo},
            block_for_target_time=False,
        )

    def _on_mpv_update(self):
        if self._updates_enabled:
            self.render_update.emit()

    def _on_swap(self):
        if self._ctx is not None:
            self._ctx.report_swap()

    def play_file(self, path: str, *, start_at: float | None = None):
        self._pending_path = path
        self._start_at = start_at
        if self._ctx is not None:
            self._flush_pending_load()
        else:
            self.update()

    def _flush_pending_load(self) -> None:
        if self._pending_path is None:
            return
        path = self._pending_path
        self._pending_path = None
        logger.info("mpv loadfile: %s", _redact_uri(path))
        self.mpv.loadfile(path, "replace")
        self.mpv.pause = False
        self.update()

    def stop(self):
        self.mpv.command("stop")

    def shutdown(self):
        self._updates_enabled = False
        self.makeCurrent()
        if self._ctx is not None:
            self._ctx.update_cb = None
            self._ctx.free()
            self._ctx = None
        player = self.mpv
        self.mpv = None
        if player is not None:
            try:
                player.quit()
            except (get_mpv().ShutdownError, AttributeError, OSError):
                pass
            try:
                player.terminate()
            except (AttributeError, OSError):
                pass
        self.doneCurrent()


def _redact_uri(uri: str) -> str:
    if "://" not in uri or "@" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    _auth, host_part = rest.split("@", 1)
    return f"{scheme}://***@{host_part}"
