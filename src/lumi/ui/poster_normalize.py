"""Shared poster crop/scaling helpers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from lumi.ui.theme.spacing import POSTER_REFERENCE_HEIGHT, POSTER_REFERENCE_WIDTH


def normalize_poster_image(image: QImage) -> QImage:
    """Crop every poster to the same 2:3 frame so swaps do not jump."""
    if image.isNull():
        return image
    scaled = image.scaled(
        POSTER_REFERENCE_WIDTH,
        POSTER_REFERENCE_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        return image
    x = max(0, (scaled.width() - POSTER_REFERENCE_WIDTH) // 2)
    return scaled.copy(x, 0, POSTER_REFERENCE_WIDTH, POSTER_REFERENCE_HEIGHT)


def normalize_poster_pixmap(pixmap: QPixmap) -> QPixmap:
    """Crop every poster to the same 2:3 frame so swaps do not jump."""
    if pixmap.isNull():
        return pixmap
    return QPixmap.fromImage(normalize_poster_image(pixmap.toImage()))
