"""Tag sidebar drawer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QEnterEvent, QFocusEvent, QGuiApplication, QKeyEvent, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lumi.ui.components.keyboard_helpers import is_back_key
from lumi.ui.icons.material_icons import IconKind, paint_icon
from lumi.ui.components.scroll_edge_fades import ScrollEdgeFadeOverlay
from lumi.ui.theme.colors import SIDEBAR_BG, SIDEBAR_FOCUS_BG, SIDEBAR_LABEL, SIDEBAR_TEXT, WHITE
from lumi.ui.theme.spacing import (
    CORNER_RADIUS_SM,
    DRAWER_WIDTH,
    SIDEBAR_CONTENT_MARGINS,
    SIDEBAR_MENU_ICON_GAP,
    SIDEBAR_MENU_ICON_SIZE,
    SIDEBAR_MENU_ITEM_HEIGHT,
    SIDEBAR_MENU_PAD_H,
    SIDEBAR_MENU_PAD_V,
    SIDEBAR_MENU_SPACING,
    SIDEBAR_SECTION_SPACING,
)
from lumi.ui.theme.styles import apply_widget_stylesheet

_ALL_TAGS = object()
_REBUILD_ITEM = object()
_SIDEBAR_MENU_HOVER_BG = QColor(26, 35, 103, 89)


class SidebarIconMenuButton(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        icon_kind: IconKind,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("menuItemWithIcon")
        self.setText("")
        self._label = text
        self._icon_kind = icon_kind
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:
        text_width = self.fontMetrics().horizontalAdvance(self._label)
        width = (
            SIDEBAR_MENU_PAD_H
            + SIDEBAR_MENU_ICON_SIZE
            + SIDEBAR_MENU_ICON_GAP
            + text_width
            + SIDEBAR_MENU_PAD_H
        )
        return QSize(width, SIDEBAR_MENU_ITEM_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, SIDEBAR_MENU_ITEM_HEIGHT)

    def enterEvent(self, event: QEnterEvent) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self.update()
        super().focusOutEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        if self.hasFocus():
            background = QColor(SIDEBAR_FOCUS_BG)
            text_color = QColor(WHITE)
        elif self.underMouse():
            background = _SIDEBAR_MENU_HOVER_BG
            text_color = QColor(SIDEBAR_TEXT)
        else:
            background = None
            text_color = QColor(SIDEBAR_TEXT)

        if background is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(rect, CORNER_RADIUS_SM, CORNER_RADIUS_SM)

        icon_top = rect.y() + (rect.height() - SIDEBAR_MENU_ICON_SIZE) // 2
        icon_rect = QRect(
            rect.x() + SIDEBAR_MENU_PAD_H,
            icon_top,
            SIDEBAR_MENU_ICON_SIZE,
            SIDEBAR_MENU_ICON_SIZE,
        )
        paint_icon(painter, icon_rect, self._icon_kind, QColor(SIDEBAR_LABEL))

        text_left = icon_rect.right() + SIDEBAR_MENU_ICON_GAP + 1
        metrics = self.fontMetrics()
        text_baseline = rect.y() + (rect.height() + metrics.ascent() - metrics.descent()) // 2
        painter.setPen(text_color)
        painter.setFont(self.font())
        painter.drawText(text_left, text_baseline, self._label)


class Sidebar(QFrame):
    tag_filter_changed = Signal(object)
    rebuild_requested = Signal()
    navigate_to_entries = Signal()
    drawer_opened = Signal()
    drawer_closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        apply_widget_stylesheet(self, Path(__file__).with_suffix(".qss"))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedWidth(DRAWER_WIDTH)

        self._open = False
        self._active_tag: str | None = None
        self._tag_buttons: list[QPushButton] = []
        self._slide_animation: QPropertyAnimation | None = None
        self._rebuilding_menu = False
        self._cached_tags: list[str] = []
        self._keyboard_focus_tag: object = _ALL_TAGS

        self._rebuild_button = SidebarIconMenuButton(
            "Rebuild library",
            icon_kind=IconKind.REFRESH,
        )
        self._rebuild_button.clicked.connect(self.rebuild_requested.emit)
        self._register_menu_item(self._rebuild_button)

        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        tags_label = QLabel("TAGS")
        tags_label.setObjectName("sectionLabel")
        tags_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tags_label.setAutoFillBackground(False)

        self._tags_container = QWidget()
        self._tags_container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tags_container.setAutoFillBackground(False)
        self._tags_layout = QVBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(SIDEBAR_MENU_SPACING)

        scroll = QScrollArea()
        scroll.setObjectName("tagsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._tags_container)
        self._tags_fade_overlay = ScrollEdgeFadeOverlay(
            scroll.verticalScrollBar(),
            parent=scroll.viewport(),
            background=QColor(SIDEBAR_BG),
        )
        self._tags_scroll = scroll

        layout = QVBoxLayout(self)
        left, top, right, bottom = SIDEBAR_CONTENT_MARGINS
        layout.setContentsMargins(left, top, right, bottom)
        layout.addWidget(self._rebuild_button)
        layout.addSpacing(SIDEBAR_SECTION_SPACING)
        layout.addWidget(divider)
        layout.addSpacing(SIDEBAR_SECTION_SPACING)
        layout.addWidget(tags_label)
        layout.addWidget(scroll, stretch=1)

        self.hide()
        self._set_menu_focusable(False)

        app = QGuiApplication.instance()
        if isinstance(app, QGuiApplication):
            app.installEventFilter(self)
            app.focusChanged.connect(self._on_focus_changed)  # type: ignore[attr-defined]

    def set_tags(self, tags: list[str]) -> None:
        if tags == self._cached_tags:
            return

        self._rebuilding_menu = True
        try:
            self._cached_tags = list(tags)
            while self._tags_layout.count():
                item = self._tags_layout.takeAt(0)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None:
                    widget.removeEventFilter(self)
                    widget.deleteLater()
            self._tag_buttons.clear()

            all_button = self._make_tag_button("All", None)
            self._tags_layout.addWidget(all_button)
            for tag in tags:
                label = tag[:1].upper() + tag[1:] if tag else tag
                self._tags_layout.addWidget(self._make_tag_button(label, tag))
            self._tags_layout.addStretch(1)
            self._update_tab_order()
        finally:
            self._rebuilding_menu = False

        self._sync_tags_fade_overlay()
        self._set_menu_focusable(self._open)

        if self._open:
            QTimer.singleShot(0, self.restore_menu_focus)

    def set_active_tag(self, tag: str | None) -> None:
        self._active_tag = tag

    def open_drawer(self) -> None:
        if self._open:
            return
        self._open = True
        self._set_menu_focusable(True)
        self.show()
        self.raise_()
        self._animate_slide(opening=True)
        self.drawer_opened.emit()

    def close_drawer(self) -> None:
        if not self._open:
            return
        self._remember_keyboard_focus()
        self._open = False
        self._set_menu_focusable(False)
        self._animate_slide(opening=False)
        self.drawer_closed.emit()

    def _remember_keyboard_focus(self) -> None:
        focused = QApplication.focusWidget()
        if focused is self._rebuild_button:
            self._keyboard_focus_tag = _REBUILD_ITEM
        elif focused in self._tag_buttons:
            self._keyboard_focus_tag = self._button_tag_value(focused)

    def _set_menu_focusable(self, focusable: bool) -> None:
        policy = Qt.FocusPolicy.StrongFocus if focusable else Qt.FocusPolicy.NoFocus
        for button in self._menu_items():
            button.setFocusPolicy(policy)

    def is_open(self) -> bool:
        return self._open

    def focus_first_item(self) -> None:
        self.open_drawer()
        self.restore_menu_focus()
        QTimer.singleShot(0, self.restore_menu_focus)

    def restore_menu_focus(self) -> None:
        if not self._open:
            return
        if self._keyboard_focus_tag is _REBUILD_ITEM:
            self._rebuild_button.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        if self._keyboard_focus_tag is _ALL_TAGS:
            self._focus_menu_item_for_tag(self._active_tag)
            return
        if isinstance(self._keyboard_focus_tag, str):
            self._focus_menu_item_for_tag(self._keyboard_focus_tag)
            return
        self._focus_menu_item_for_tag(None)

    def sync_geometry(self, host_width: int, host_height: int) -> None:
        if self._is_animating():
            self.resize(DRAWER_WIDTH, host_height)
            return
        x = host_width - DRAWER_WIDTH if self._open else host_width
        self.setGeometry(x, 0, DRAWER_WIDTH, host_height)
        self._sync_tags_fade_overlay()

    def _sync_tags_fade_overlay(self) -> None:
        self._tags_fade_overlay.sync()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_tags_fade_overlay()

    def _is_animating(self) -> bool:
        return (
            self._slide_animation is not None
            and self._slide_animation.state() == QPropertyAnimation.State.Running
        )

    def _animate_slide(self, *, opening: bool) -> None:
        parent = self.parentWidget()
        if parent is None:
            if not opening:
                self.hide()
            return

        if self._slide_animation is not None:
            self._slide_animation.stop()

        start_x = parent.width() if opening else self.x()
        end_x = parent.width() - DRAWER_WIDTH if opening else parent.width()
        self.setGeometry(start_x, 0, DRAWER_WIDTH, parent.height())

        animation = QPropertyAnimation(self, b"pos", self)
        animation.setDuration(180)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(self.pos())
        animation.setEndValue(self.pos().__class__(end_x, 0))

        def on_finished() -> None:
            self._slide_animation = None
            if opening:
                self.sync_geometry(parent.width(), parent.height())
            else:
                self.hide()

        animation.finished.connect(on_finished)
        self._slide_animation = animation
        animation.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._open and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if isinstance(key_event, QKeyEvent):
                if self._handle_open_key_press(key_event, watched):
                    return True

        items = self._menu_items()
        if watched not in items:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.FocusIn:
            if watched is self._rebuild_button:
                self._keyboard_focus_tag = _REBUILD_ITEM
            elif watched in self._tag_buttons:
                self._keyboard_focus_tag = self._button_tag_value(watched)
            return False

        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(watched, event)

        key_event = event
        if not isinstance(key_event, QKeyEvent):
            return super().eventFilter(watched, event)

        if self._handle_open_key_press(key_event, watched):
            return True

        index = items.index(watched)
        key = key_event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            watched.click()
            return True
        if key == Qt.Key.Key_Down and index < len(items) - 1:
            items[index + 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True
        if key == Qt.Key.Key_Up and index > 0:
            items[index - 1].setFocus(Qt.FocusReason.TabFocusReason)
            return True

        return super().eventFilter(watched, event)

    def _handle_open_key_press(self, key_event: QKeyEvent, watched: QObject) -> bool:
        focused = QApplication.focusWidget()
        in_sidebar = focused is not None and self.isAncestorOf(focused)
        key = key_event.key()

        if in_sidebar and (key in (Qt.Key.Key_Left, Qt.Key.Key_Right) or is_back_key(key)):
            self._remember_keyboard_focus()
            self.navigate_to_entries.emit()
            return True

        if (
            key in (Qt.Key.Key_Down, Qt.Key.Key_Up)
            and watched in self._menu_items()
        ):
            return False

        if not in_sidebar and key in (Qt.Key.Key_Left, Qt.Key.Key_Down, Qt.Key.Key_Up):
            return False

        return False

    def _on_focus_changed(self, old: QWidget | None, new: QWidget | None) -> None:
        if not self._open or self._rebuilding_menu:
            return
        if new is not None and (new is self or self.isAncestorOf(new)):
            return
        if old is None or not (old is self or self.isAncestorOf(old)):
            return
        QTimer.singleShot(0, self._ensure_menu_focus_or_close)

    def _ensure_menu_focus_or_close(self) -> None:
        try:
            if not self._open or self._rebuilding_menu:
                return
            focused = QApplication.focusWidget()
            if focused is not None and self.isAncestorOf(focused):
                return
            self.restore_menu_focus()
            focused = QApplication.focusWidget()
            if focused is not None and self.isAncestorOf(focused):
                return
            self.close_drawer()
        except RuntimeError:
            return

    def _menu_items(self) -> list[QPushButton]:
        return [self._rebuild_button, *self._tag_buttons]

    def _register_menu_item(self, item: QPushButton) -> None:
        item.setAutoDefault(False)
        item.setDefault(False)
        item.setFlat(True)
        item.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        item.installEventFilter(self)

    def _make_tag_button(self, label: str, tag: str | None) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("menuItem")
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setProperty("tagValue", "" if tag is None else tag)
        button.clicked.connect(lambda checked=False, t=tag: self._select_tag(t))
        self._tag_buttons.append(button)
        self._register_menu_item(button)
        return button

    def _select_tag(self, tag: str | None) -> None:
        self._active_tag = tag
        self._keyboard_focus_tag = tag
        self.tag_filter_changed.emit(tag)
        QTimer.singleShot(0, self.restore_menu_focus)

    def _button_tag_value(self, button: QPushButton) -> str | None:
        raw = button.property("tagValue")
        if raw is None or raw == "":
            return None
        return str(raw)

    def _focus_menu_item_for_tag(self, tag: str | None) -> None:
        for button in self._tag_buttons:
            if self._button_tag_value(button) == tag:
                button.setFocus(Qt.FocusReason.OtherFocusReason)
                return
        self._rebuild_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _update_tab_order(self) -> None:
        items = self._menu_items()
        for previous, current in zip(items, items[1:], strict=False):
            QWidget.setTabOrder(previous, current)
