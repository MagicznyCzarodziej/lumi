"""TV-friendly UI scale tokens (pure functions, no mpv)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiMetrics:
    """Shared scale tokens for controls, hints, and track sidebars (TV-friendly)."""

    scale: int
    margin: int
    gap: int
    font_sm: int
    font_md: int
    font_lg: int
    btn_sm: int
    btn_md: int
    btn_lg: int
    hint_size: int
    hint_gap: int
    hint_label_gap: int
    panel_w_min: int
    track_pad_x: int
    track_pad_y: int
    track_font: int
    track_title_font: int
    track_row_h: int
    pad: int
    radius_sm: int
    accent_bar_w: int
    bottom_pad: int


def compute_ui_metrics(w: int, h: int) -> UiMetrics:
    scale = min(w, h)
    margin = max(20, int(w * 0.04))
    gap = max(10, int(w * 0.008))
    font_sm = max(12, min(22, int(scale * 0.022)))
    font_md = max(14, min(24, int(scale * 0.026)))
    font_lg = max(16, min(28, int(scale * 0.032)))
    track_font = max(18, min(30, int(scale * 0.032)))
    track_title_font = max(22, min(36, int(scale * 0.04)))
    btn_sm = max(48, min(int(scale * 0.068), 96))
    btn_md = max(52, min(int(scale * 0.082), 108))
    btn_lg = max(56, min(int(scale * 0.09), 128))
    track_row_h = max(btn_md, track_font + max(12, int(scale * 0.016)))
    track_pad_x = max(18, int(scale * 0.02))
    track_pad_y = max(20, int(scale * 0.022))
    return UiMetrics(
        scale=scale,
        margin=margin,
        gap=gap,
        font_sm=font_sm,
        font_md=font_md,
        font_lg=font_lg,
        btn_sm=btn_sm,
        btn_md=btn_md,
        btn_lg=btn_lg,
        hint_size=btn_sm,
        hint_gap=gap,
        hint_label_gap=max(12, int(font_sm * 0.95)),
        panel_w_min=max(340, int(scale * 0.22)),
        track_pad_x=track_pad_x,
        track_pad_y=track_pad_y,
        track_font=track_font,
        track_title_font=track_title_font,
        track_row_h=track_row_h,
        pad=margin,
        radius_sm=max(8, int(btn_sm * 0.14)),
        accent_bar_w=max(4, int(scale * 0.005)),
        bottom_pad=max(28, int(h * 0.035)),
    )


def fmt_time(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "0:00"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
