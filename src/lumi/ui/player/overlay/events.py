"""Qt input and paint events for the player overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PySide6.QtWidgets import QWidget

from lumi.domain.video_aspect import video_aspect_label
from lumi.ui.player.overlay.input_router import Command
from lumi.ui.player.overlay.paint.browse import paint_browse_sheet
from lumi.ui.player.overlay.paint.controls import (
    paint_corner_hints,
    paint_cross_controls,
    paint_episode_title,
    paint_timeline,
)
from lumi.ui.player.overlay.paint.tracks import paint_track_sheet
from lumi.ui.player.overlay.paint.video import paint_video_sheet
from lumi.ui.player.overlay.paint.volume import paint_volume
from lumi.ui.player.overlay.state import View

if TYPE_CHECKING:
    from lumi.ui.player.overlay.overlay import PlayerOverlay


class OverlayEvents:
    __slots__ = ("_overlay",)

    def __init__(self, overlay: PlayerOverlay) -> None:
        self._overlay = overlay

    @property
    def _o(self) -> PlayerOverlay:
        return self._overlay

    @property
    def _rt(self):
        return self._overlay._rt

    def keyPressEvent(self, event) -> None:
        if routed := self._rt.router.route_key(
            event, self._rt.state, has_media=self._rt.controller.has_media()
        ):
            if not event.isAutoRepeat():
                if key := self._o.press_key_for_command(routed):
                    self._o.activity.begin_press(key)
            self._o.execute_command(routed)
            if routed.command != Command.SHOW_CONTROLS or self._rt.state.view != View.WATCHING:
                event.accept()
                return
        QWidget.keyPressEvent(self._o, event)

    def keyReleaseEvent(self, event) -> None:
        self._o.activity.end_press()
        if routed := self._rt.router.route_key_release(event, self._rt.state):
            self._o.execute_command(routed)
            event.accept()
            return
        QWidget.keyReleaseEvent(self._o, event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._rt.state.view in (View.TRACKS, View.VIDEO, View.SUBTITLE_BROWSE):
            delta = event.angleDelta().y()
            if delta != 0:
                self._o.activity.scroll_panel_by(delta)
                event.accept()
                return
        QWidget.wheelEvent(self._o, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        scrub = self._rt.state.scrub
        if scrub and scrub.seek_dragging:
            self._o.scrub.seek_at(event.position().toPoint())
            return
        if self._o.activity.tracks_inactivity():
            self._o.activity.note_ui_activity()
        if routed := self._rt.router.route_mouse_move(self._rt.state, scrubbing=False):
            if routed.command == Command.SHOW_CONTROLS:
                self._o.activity.show_controls()
        QWidget.mouseMoveEvent(self._o, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._o.activity.end_press()
        scrub = self._rt.state.scrub
        if routed := self._rt.router.route_mouse_release(
            event, scrubbing=bool(scrub and scrub.seek_dragging)
        ):
            self._o.execute_command(routed)
            return
        self._o.update()
        QWidget.mouseReleaseEvent(self._o, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._rt.state.view in (View.CONTROLS, View.TRACKS, View.VIDEO, View.SCRUB, View.SUBTITLE_BROWSE):
            self._o.panel.rebuild()
        routed = self._rt.router.route_mouse_press(
            event,
            self._rt.state,
            self._rt.layout.hit_regions,
            has_media=self._rt.controller.has_media(),
            in_controls_area=lambda pos: any(
                r.contains(pos) for r in self._rt.layout.hit_regions.values()
            ),
        )
        if routed:
            if key := self._o.press_key_for_command(routed):
                self._o.activity.begin_press(key)
            self._o.execute_command(routed)
            return
        QWidget.mousePressEvent(self._o, event)

    def paintEvent(self, _event: QPaintEvent) -> None:
        w, h = self._o.width(), self._o.height()
        if not self._rt.controller.has_media():
            self._o.activity.after_paint_anim()
            return

        if self._rt.state.view == View.WATCHING:
            if self._rt.state.volume_flash:
                painter = QPainter(self._o)
                if painter.isActive():
                    try:
                        painter.save()
                        painter.setOpacity(self._rt.ui_opacity)
                        paint_volume(painter, w, h, self._rt.state.volume, muted=self._rt.state.muted)
                        painter.restore()
                    finally:
                        painter.end()
            self._o.activity.after_paint_anim()
            return

        self._o.panel.rebuild()
        press_key, press_strength_val = self._o.activity.press_state()
        painter = QPainter(self._o)
        if not painter.isActive():
            return
        try:
            painter.save()
            painter.setOpacity(self._rt.ui_opacity)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if self._rt.state.view == View.CONTROLS:
                paint_episode_title(
                    painter,
                    self._rt.layout,
                    title=self._rt.episode_title,
                    viewport_w=w,
                )
                paint_cross_controls(
                    painter,
                    self._rt.state,
                    self._rt.layout,
                    playing=self._rt.controller.is_playing(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
                paint_corner_hints(
                    painter,
                    self._rt.layout,
                    subtitle_name=self._rt.controller.current_subtitle_label(),
                    audio_name=self._rt.controller.current_audio_label(),
                    video_name=video_aspect_label(self._rt.controller.video_aspect_mode()),
                )
                if self._rt.state.volume_flash:
                    paint_volume(painter, w, h, self._rt.state.volume, muted=self._rt.state.muted)
            elif self._rt.state.view == View.SCRUB:
                paint_episode_title(
                    painter,
                    self._rt.layout,
                    title=self._rt.episode_title,
                    viewport_w=w,
                )
                paint_timeline(
                    painter,
                    self._rt.state,
                    self._rt.layout,
                    timeline_focused=True,
                )
            elif self._rt.state.view == View.TRACKS:
                painter.fillRect(self._o.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_track_sheet(
                    painter,
                    w,
                    h,
                    self._rt.state,
                    self._rt.layout,
                    sid=self._rt.controller.current_sid(),
                    aid=self._rt.controller.current_aid(),
                    sub_delay=self._rt.controller.sub_delay(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
            elif self._rt.state.view == View.VIDEO:
                painter.fillRect(self._o.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_video_sheet(
                    painter,
                    w,
                    h,
                    self._rt.state,
                    self._rt.layout,
                    current_mode_index=self._rt.controller.video_aspect_mode_index(),
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
            elif self._rt.state.view == View.SUBTITLE_BROWSE:
                painter.fillRect(self._o.rect(), QColor.fromRgbF(0, 0, 0, 0.42))
                paint_browse_sheet(
                    painter,
                    w,
                    h,
                    self._rt.state,
                    self._rt.layout,
                    press_key=press_key,
                    press_strength=press_strength_val,
                )
        finally:
            painter.restore()
            painter.end()

        self._o.activity.after_paint_anim()
