"""Левая панель навигации по разделам приложения.

Входные данные:
    События кликов пользователя и параметры родительского виджета.

Выходные данные:
    Обновление активного раздела и генерация сигналов.
"""

import qtawesome as qta
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QSizePolicy, QButtonGroup
from PySide6.QtCore import Qt, QSize


class LeftRail(QWidget):
    """Узкая левая панель с иконками QtAwesome и подсказками."""

    WIDTH = 56

    def __init__(self, parent=None):
        """Инициализирует кнопки и стиль панели навигации."""
        super().__init__(parent)
        self.setFixedWidth(self.WIDTH)
        self.setObjectName("LeftRail")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(8)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self._icon_color = "#cfcfcf"
        self._icon_color_active = "#ffffff"

        self._icons = {
            "Проекты": "fa5s.folder-open",
            "Задачи": "fa5s.tasks",
            "Карты": "fa5s.map",
            "Заметки": "fa5s.sticky-note",
            "Файлы": "fa5s.file-alt",
            "Объекты": "fa5s.cube",
            "Настройки": "fa5s.cog",
        }

        def btn(icon_name: str, tooltip: str) -> QToolButton:
            """Создает кнопку панели с иконкой и подсказкой."""
            b = QToolButton()
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tooltip)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setFixedHeight(36)
            b.setIconSize(QSize(20, 20))
            b.setProperty("qta_name", icon_name)
            self.group.addButton(b)
            layout.addWidget(b)
            return b

        self.btn_projects = btn(self._icons["Проекты"], "Проекты")
        self.btn_tasks = btn(self._icons["Задачи"], "Задачи")
        self.btn_maps = btn(self._icons["Карты"], "Карты")
        self.btn_notes = btn(self._icons["Заметки"], "Заметки")
        self.btn_files = btn(self._icons["Файлы"], "Файлы")
        self.btn_objects = btn(self._icons["Объекты"], "Объекты")

        layout.addStretch(1)
        self.btn_settings = btn(self._icons["Настройки"], "Настройки")

        self.btn_tasks.setChecked(True)

        for b in self.group.buttons():
            b.toggled.connect(self._refresh_icons)
        self._refresh_icons()

        self.setStyleSheet("""
            QWidget#LeftRail {
                background: #1e1f22;
                border-right: 1px solid #2a2b2f;
            }
            QToolButton {
                border: none;
                border-radius: 8px;
                padding: 6px;
                background: transparent;
            }
            QToolButton:hover { background: #2a2b2f; }
            QToolButton:checked { background: #35363c; }
            QToolTip {
                background-color: #2a2b2f;
                color: #e0e0e0;
                border: 1px solid #3a3b40;
                padding: 6px;
            }
        """)

    def _refresh_icons(self):
        """Обновляет цвет иконок в зависимости от выбранной кнопки."""
        for b in self.group.buttons():
            name = b.property("qta_name")
            if not name:
                continue
            color = self._icon_color_active if b.isChecked() else self._icon_color
            b.setIcon(qta.icon(name, color=color))
