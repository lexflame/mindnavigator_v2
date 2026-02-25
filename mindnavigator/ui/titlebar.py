"""Кастомный заголовок окна приложения.

Входные данные:
    События мыши и ссылки на родительское окно.

Выходные данные:
    Управление перемещением/размером окна и обработкой кнопок.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QMainWindow
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPoint

from ..constants import APP_NAME
from ..resources import resource_path
from .styles import TITLEBAR_BACKGROUND


class TitleBar(QWidget):
    """Кастомный заголовок окна: перетаскивание, двойной клик и кнопки."""

    HEIGHT = 40

    def __init__(self, parent_window: QMainWindow):
        """Создает заголовок и связывает кнопки управления окном."""
        super().__init__(parent_window)
        self._window = parent_window

        self._dragging = False
        self._drag_pos = QPoint()
        self._press_global = QPoint()
        self._press_initiated = False

        self.setFixedHeight(self.HEIGHT)
        self.setObjectName("TitleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        pm = QPixmap(resource_path("assets/icon.ico"))
        if not pm.isNull():
            self.icon_label.setPixmap(
                pm.scaled(
                    18,
                    18,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            )
        self.icon_label.setFixedSize(18, 18)

        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("TitleText")

        self.btn_min = QToolButton()
        self.btn_max = QToolButton()
        self.btn_close = QToolButton()

        self.btn_min.setText("–")
        self.btn_max.setText("□")
        self.btn_close.setText("×")

        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setFixedSize(34, 26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        if hasattr(self._window, "minimize_to_tray"):
            self.btn_min.clicked.connect(self._window.minimize_to_tray)
        else:
            self.btn_min.clicked.connect(self._window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(self._window.close)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

        self.setStyleSheet(f"""
            QWidget#TitleBar {{
                {TITLEBAR_BACKGROUND}
                border-bottom: 1px solid #2a2b2f;
            }}
            QLabel#TitleText {{
                color: #eef1ff;
                font-size: 13px;
                font-weight: 600;
            }}
            QToolButton {{
                color: #cfcfcf;
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QToolButton:hover {{ background: #2a2b2f; }}
            QToolButton:pressed {{ background: #35363c; }}
            QToolButton:last-child:hover {{
                background: #b23b3b;
                color: #ffffff;
            }}
        """)

    def sync_max_button(self):
        """Синхронизирует иконку кнопки maximize с состоянием окна."""
        self.btn_max.setText("❐" if self._window.isMaximized() else "□")

    def _toggle_max_restore(self):
        """Переключает окно между нормальным и развернутым состояниями."""
        if not self._window.isMaximized() and hasattr(self._window, "_restore_geom"):
            self._window._restore_geom = self._window.geometry()

        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

        self.sync_max_button()

    def mousePressEvent(self, e):
        """Запоминает старт перетаскивания заголовка."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_initiated = True
            self._press_global = e.globalPosition().toPoint()

            if not self._window.isMaximized():
                self._dragging = True
                self._drag_pos = self._press_global - self._window.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        """Перемещает окно или выводит из maximize при перетаскивании."""
        if not self._dragging:
            return

        if self._window.isMaximized():
            # 1) вычисляем позицию курсора внутри titlebar (доля)
            ratio = e.position().x() / max(1, self.width())

            # 2) восстанавливаем нормальное окно
            self._window.showNormal()

            # 3) ставим так, чтобы курсор остался над тем же местом окна
            geo = self._window.geometry()
            new_x = e.globalPosition().toPoint().x() - int(geo.width() * ratio)
            new_y = e.globalPosition().toPoint().y() - int(self.height() / 2)
            self._window.move(new_x, new_y)

            # 4) обновляем drag offset и продолжаем
            self._drag_pos = e.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            self.sync_max_button()

        self._window.move(e.globalPosition().toPoint() - self._drag_pos)
        e.accept()

    def mouseReleaseEvent(self, e):
        """Завершает перетаскивание и применяет прилипания к краям."""
        if e.button() == Qt.MouseButton.LeftButton:
            global_pos = e.globalPosition().toPoint()
            self._press_initiated = False
            self._dragging = False

            if hasattr(self._window, "snap_to_screen_edges"):
                self._window.snap_to_screen_edges(global_pos)

            e.accept()
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        """Обрабатывает двойной клик для разворота окна."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._toggle_max_restore()
            e.accept()
