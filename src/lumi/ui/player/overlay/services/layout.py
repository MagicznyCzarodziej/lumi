from __future__ import annotations

from lumi.ui.player.overlay.layout.regions import compute_layout
from lumi.ui.player.overlay.layout.panel_scroll import scroll_to_show_item
from lumi.ui.player.overlay.services.base import OverlayService
from lumi.ui.player.overlay.state import View


class LayoutService(OverlayService):
    def rebuild(self) -> None:
        rows = self._rt.state.track_rows or []
        self._rt.layout = compute_layout(
            self._o.width(),
            self._o.height(),
            self._rt.state.view,
            self._rt.state.track_kind,
            rows,
            browse_path=self._rt.state.browse_path,
            browse_rows=self._rt.state.browse_rows,
            panel_scroll_y=self._rt.state.panel_scroll_y,
        )
        self._rt.state.panel_scroll_y = self._rt.layout.panel_scroll_y
        self._rt.state.panel_w = self._rt.layout.panel_w

    def panel_focus_key(self) -> str | None:
        if self._rt.state.view == View.TRACKS:
            return f"track:{self._rt.state.track_focus}"
        if self._rt.state.view == View.VIDEO:
            return f"video:{self._rt.state.video_focus}"
        if self._rt.state.view == View.SUBTITLE_BROWSE:
            return f"browse:{self._rt.state.browse_focus}"
        return None

    def ensure_panel_focus_visible(self) -> None:
        focus_key = self.panel_focus_key()
        if focus_key is None:
            return
        content_top = self._rt.layout.panel_row_tops.get(focus_key)
        rect = self._rt.layout.hit_regions.get(focus_key)
        if content_top is None or rect is None:
            return
        new_scroll = scroll_to_show_item(
            content_top,
            rect.height(),
            viewport_top=self._rt.layout.panel_list_top,
            viewport_bottom=self._rt.layout.panel_list_bottom,
            scroll_y=self._rt.state.panel_scroll_y,
        )
        if new_scroll == self._rt.state.panel_scroll_y:
            return
        self._rt.state.panel_scroll_y = new_scroll
        self.rebuild()
