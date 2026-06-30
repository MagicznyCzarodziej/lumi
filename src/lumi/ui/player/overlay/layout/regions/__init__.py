"""Hit-region layout — re-exports the public regions API."""

from lumi.ui.player.overlay.layout.regions.browse import browse_panel_width, browse_row_height
from lumi.ui.player.overlay.layout.regions.compute import compute_layout
from lumi.ui.player.overlay.layout.regions.controls import layout_controls_geometry
from lumi.ui.player.overlay.layout.regions.fonts import time_label_width, ui_font
from lumi.ui.player.overlay.layout.regions.idle import layout_idle_regions
from lumi.ui.player.overlay.layout.regions.tracks import (
    layout_track_panel,
    split_track_panel_rows,
    track_footer_extent_height,
    track_panel_width,
    track_row_height,
)
from lumi.ui.player.overlay.layout.regions.types import HitRegion, LayoutSnapshot
from lumi.ui.player.overlay.layout.regions.video import video_panel_width

__all__ = [
    "HitRegion",
    "LayoutSnapshot",
    "browse_panel_width",
    "browse_row_height",
    "compute_layout",
    "layout_controls_geometry",
    "layout_idle_regions",
    "layout_track_panel",
    "split_track_panel_rows",
    "time_label_width",
    "track_footer_extent_height",
    "track_panel_width",
    "track_row_height",
    "ui_font",
    "video_panel_width",
]
