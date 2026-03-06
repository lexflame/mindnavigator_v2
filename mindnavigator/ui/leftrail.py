"""Left sidebar mode rail with icon buttons and hover expansion panel."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QEvent, QTimer, Qt, QSize, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from .animations import WidthExpandAnimationConfig, WidthExpandAnimator


class LeftRail(QWidget):
    """Compact left rail with mode icons and hover expansion labels."""

    theme_toggled = Signal(str)

    WIDTH = 56
    HOVER_PANEL_WIDTH = 220
    HOVER_ANIMATION_MS = 130

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setObjectName("LeftRail")
        self.setMouseTracking(True)

        self._hover_host: QWidget | None = None
        self._hover_panel: QFrame | None = None
        self._hover_animator: WidthExpandAnimator | None = None
        self._hover_labels: dict[str, QLabel] = {}
        self._hover_collapsed_width = 1
        self._is_hover_expanded = False

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(110)
        self._collapse_timer.timeout.connect(self._collapse_if_cursor_outside)

        self._hide_panel_timer = QTimer(self)
        self._hide_panel_timer.setSingleShot(True)
        self._hide_panel_timer.setInterval(self.HOVER_ANIMATION_MS + 30)
        self._hide_panel_timer.timeout.connect(self._hide_hover_panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(8)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self._icon_color = "#cfcfcf"
        self._icon_color_active = "#ffffff"
        self._theme_mode = "dark"

        self._icons = {
            "Проекты": "fa5s.folder-open",
            "Задачи": "fa5s.tasks",
            "Покупки": "fa5s.shopping-cart",
            "Идеи": "fa5s.lightbulb",
            "Коллекции": "fa5s.project-diagram",
            "Карты": "fa5s.map",
            "Заметки": "fa5s.sticky-note",
            "Файлы": "fa5s.file-alt",
            "Объекты": "fa5s.cube",
            "Персонажи": "fa5s.user-friends",
            "MindDraw": "fa5s.sitemap",
            "Настройки": "fa5s.cog",
        }

        def btn(icon_name: str, tooltip: str) -> QToolButton:
            rail_button = QToolButton()
            rail_button.setCheckable(True)
            rail_button.setCursor(Qt.CursorShape.PointingHandCursor)
            rail_button.setToolTip(tooltip)
            rail_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            rail_button.setFixedHeight(36)
            rail_button.setIconSize(QSize(20, 20))
            rail_button.setProperty("qta_name", icon_name)
            rail_button.setMouseTracking(True)
            self.group.addButton(rail_button)
            layout.addWidget(rail_button)
            return rail_button

        self.btn_projects = btn(self._icons["Проекты"], "Проекты")
        self.btn_tasks = btn(self._icons["Задачи"], "Задачи")
        self.btn_purchases = btn(self._icons["Покупки"], "Покупки")
        self.btn_ideas = btn(self._icons["Идеи"], "Идеи")
        self.btn_collections = btn(self._icons["Коллекции"], "Коллекции")
        self.btn_maps = btn(self._icons["Карты"], "Карты")
        self.btn_notes = btn(self._icons["Заметки"], "Заметки")
        self.btn_files = btn(self._icons["Файлы"], "Файлы")
        self.btn_objects = btn(self._icons["Объекты"], "Объекты")
        self.btn_characters = btn(self._icons["Персонажи"], "Персонажи")
        self.btn_minddraw = btn(self._icons["MindDraw"], "MindDraw")

        layout.addStretch(1)

        self.btn_theme_toggle = QToolButton()
        self.btn_theme_toggle.setObjectName("ThemeToggleSwitch")
        self.btn_theme_toggle.setCheckable(True)
        self.btn_theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_toggle.setFixedHeight(36)
        self.btn_theme_toggle.setIconSize(QSize(20, 20))
        self.btn_theme_toggle.clicked.connect(self._on_theme_toggle_clicked)
        layout.addWidget(self.btn_theme_toggle)

        self.btn_settings = btn(self._icons["Настройки"], "Настройки")

        self._mode_buttons = {
            "Проекты": self.btn_projects,
            "Задачи": self.btn_tasks,
            "Покупки": self.btn_purchases,
            "Идеи": self.btn_ideas,
            "Коллекции": self.btn_collections,
            "Карты": self.btn_maps,
            "Заметки": self.btn_notes,
            "Файлы": self.btn_files,
            "Объекты": self.btn_objects,
            "Персонажи": self.btn_characters,
            "MindDraw": self.btn_minddraw,
            "Настройки": self.btn_settings,
        }
        self._mode_order_top = list(self._mode_buttons.keys())[:-1]
        self._mode_order_bottom = [list(self._mode_buttons.keys())[-1]]

        self.btn_tasks.setChecked(True)

        for button in self.group.buttons():
            button.toggled.connect(self._refresh_icons)
        self._refresh_icons()

        self._apply_stylesheet()
        self.set_theme_mode(self._theme_mode)

    def _refresh_icons(self) -> None:
        for button in self.group.buttons():
            icon_name = button.property("qta_name")
            if not icon_name:
                continue
            color = self._icon_color_active if button.isChecked() else self._icon_color
            button.setIcon(qta.icon(icon_name, color=color))
        self._refresh_theme_toggle_icon()
        self.refresh_hover_panel()

    def _refresh_theme_toggle_icon(self) -> None:
        is_light = self._theme_mode == "light"
        icon_name = "fa5s.sun" if is_light else "fa5s.moon"
        icon_color = self._icon_color_active if is_light else self._icon_color
        self.btn_theme_toggle.setIcon(qta.icon(icon_name, color=icon_color))
        self.btn_theme_toggle.setToolTip("Светлая тема" if is_light else "Тёмная тема")

    def set_theme_mode(self, theme_mode: str) -> None:
        normalized = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        self._theme_mode = normalized
        self._apply_stylesheet()
        is_light = normalized == "light"
        self.btn_theme_toggle.blockSignals(True)
        self.btn_theme_toggle.setChecked(is_light)
        self.btn_theme_toggle.blockSignals(False)
        self._refresh_theme_toggle_icon()

    def _on_theme_toggle_clicked(self, checked: bool) -> None:
        self._theme_mode = "light" if checked else "dark"
        self._apply_stylesheet()
        self._refresh_theme_toggle_icon()
        self.theme_toggled.emit(self._theme_mode)

    def _apply_stylesheet(self) -> None:
        is_light = self._theme_mode == "light"
        rail_bg = "#edf1f9" if is_light else "#1e1f22"
        rail_border = "#cfd4de" if is_light else "#2a2b2f"
        button_hover = "#dbe3f5" if is_light else "#2a2b2f"
        button_checked = "#c9d6f1" if is_light else "#35363c"
        tooltip_bg = "#f3f6fc" if is_light else "#2a2b2f"
        tooltip_text = "#22304b" if is_light else "#e0e0e0"
        tooltip_border = "#c3cde0" if is_light else "#3a3b40"
        theme_border = "#b8c5e1" if is_light else "#3a3b40"
        theme_bg = "#d9e2f6" if is_light else "#22252b"
        theme_hover = "#c9d6f1" if is_light else "#2a2f38"
        theme_checked_bg = "#b8caef" if is_light else "#3b4a7a"
        theme_checked_border = "#8ca3d6" if is_light else "#5a70b3"
        self.setStyleSheet(
            f"""
            QWidget#LeftRail {{
                background: {rail_bg};
                border-right: 1px solid {rail_border};
            }}
            QToolButton {{
                border: none;
                border-radius: 8px;
                padding: 6px;
                background: transparent;
            }}
            QToolButton:hover {{ background: {button_hover}; }}
            QToolButton:checked {{ background: {button_checked}; }}
            QToolButton#ThemeToggleSwitch {{
                border: 1px solid {theme_border};
                border-radius: 8px;
                background: {theme_bg};
            }}
            QToolButton#ThemeToggleSwitch:hover {{
                background: {theme_hover};
            }}
            QToolButton#ThemeToggleSwitch:checked {{
                background: {theme_checked_bg};
                border-color: {theme_checked_border};
            }}
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_text};
                border: 1px solid {tooltip_border};
                padding: 6px;
            }}
            """
        )

    def set_mode_labels(self, labels: dict[str, str]) -> None:
        for mode_key, button in self._mode_buttons.items():
            button.setToolTip(labels.get(mode_key, mode_key))
        self.refresh_hover_panel()

    def set_expand_host(self, host: QWidget) -> None:
        if self._hover_host is host:
            return
        if self._hover_host is not None:
            self._hover_host.removeEventFilter(self)
        self._hover_host = host
        if self._hover_host is not None:
            self._hover_host.installEventFilter(self)
        self._ensure_hover_panel()
        self._reposition_hover_panel()

    def refresh_hover_panel(self) -> None:
        if self._hover_panel is None:
            return
        for mode_key, label in self._hover_labels.items():
            button = self._mode_buttons.get(mode_key)
            if button is None:
                continue
            label.setVisible(button.isVisible())
            label.setText(button.toolTip())
        self._reposition_hover_panel()

    def _ensure_hover_panel(self) -> None:
        if self._hover_host is None or self._hover_panel is not None:
            return

        panel = QFrame(self._hover_host)
        panel.setObjectName("LeftRailHoverPanel")
        panel.setMouseTracking(True)
        panel.installEventFilter(self)
        panel.setStyleSheet(
            """
            QFrame#LeftRailHoverPanel {
                background: rgba(30, 31, 34, 242);
                border: 1px solid #2f3339;
                border-radius: 10px;
            }
            QLabel#LeftRailHoverLabel {
                color: #d9dbe3;
                font-size: 12px;
                font-weight: 600;
                padding-left: 10px;
                background: transparent;
            }
            """
        )

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(8)

        for mode_key in self._mode_order_top:
            label = QLabel("", panel)
            label.setObjectName("LeftRailHoverLabel")
            label.setFixedHeight(36)
            panel_layout.addWidget(label)
            self._hover_labels[mode_key] = label

        panel_layout.addStretch(1)

        for mode_key in self._mode_order_bottom:
            label = QLabel("", panel)
            label.setObjectName("LeftRailHoverLabel")
            label.setFixedHeight(36)
            panel_layout.addWidget(label)
            self._hover_labels[mode_key] = label

        panel.setMinimumWidth(self._hover_collapsed_width)
        panel.setMaximumWidth(self._hover_collapsed_width)
        panel.hide()

        self._hover_panel = panel
        self._hover_animator = WidthExpandAnimator(
            panel,
            WidthExpandAnimationConfig(
                collapsed_width=self._hover_collapsed_width,
                expanded_width=self.HOVER_PANEL_WIDTH,
                duration_ms=self.HOVER_ANIMATION_MS,
            ),
        )
        self.refresh_hover_panel()

    def _reposition_hover_panel(self) -> None:
        if self._hover_panel is None or self._hover_host is None:
            return
        top_right = self.mapTo(self._hover_host, self.rect().topRight())
        y = max(0, min(top_right.y(), max(0, self._hover_host.height() - self.height())))
        x = max(0, top_right.x() - 1)
        self._hover_panel.move(x, y)
        self._hover_panel.setFixedHeight(self.height())

    def enterEvent(self, event) -> None:  # noqa: N802
        self._expand_hover_panel()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._schedule_collapse()
        super().leaveEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._reposition_hover_panel()
        super().resizeEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._hide_hover_panel()
        super().hideEvent(event)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._hover_host and event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
            self._reposition_hover_panel()
        if obj is self._hover_panel:
            if event.type() in (QEvent.Type.Enter, QEvent.Type.MouseMove):
                self._collapse_timer.stop()
            elif event.type() == QEvent.Type.Leave:
                self._schedule_collapse()
        return super().eventFilter(obj, event)

    def _expand_hover_panel(self) -> None:
        self._ensure_hover_panel()
        if self._hover_panel is None or self._hover_animator is None:
            return
        self._reposition_hover_panel()
        self.refresh_hover_panel()
        self._collapse_timer.stop()
        self._hide_panel_timer.stop()
        self._hover_panel.show()
        self._hover_panel.raise_()
        self._hover_animator.expand()
        self._is_hover_expanded = True

    def _schedule_collapse(self) -> None:
        if not self._is_hover_expanded:
            return
        self._collapse_timer.start()

    def _collapse_if_cursor_outside(self) -> None:
        cursor_pos = QCursor.pos()
        if self._cursor_inside_widget(self, cursor_pos):
            return
        if self._hover_panel is not None and self._cursor_inside_widget(self._hover_panel, cursor_pos):
            return
        self._collapse_hover_panel()

    def _collapse_hover_panel(self) -> None:
        if self._hover_panel is None or self._hover_animator is None:
            return
        if not self._is_hover_expanded:
            return
        self._hover_animator.collapse()
        self._is_hover_expanded = False
        self._hide_panel_timer.start()

    def _hide_hover_panel(self) -> None:
        if self._hover_panel is None:
            return
        cursor_pos = QCursor.pos()
        if self._cursor_inside_widget(self, cursor_pos):
            return
        if self._cursor_inside_widget(self._hover_panel, cursor_pos):
            return
        self._hover_panel.hide()

    @staticmethod
    def _cursor_inside_widget(widget: QWidget, cursor_pos) -> bool:
        if widget is None or not widget.isVisible():
            return False
        local_pos = widget.mapFromGlobal(cursor_pos)
        return widget.rect().contains(local_pos)
