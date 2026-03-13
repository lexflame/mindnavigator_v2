"""Кастомный заголовок окна приложения.

Входные данные:
    События мыши и ссылки на родительское окно.

Выходные данные:
    Управление перемещением/размером окна и обработкой кнопок.
"""

from collections.abc import Callable

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QFrame,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPoint, QTimer

from ..constants import APP_NAME
from mindnavigator.spaceenity.resources import resource_path
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
        self._minimized_restore_handlers: dict[int, Callable[[], None]] = {}
        self._minimized_is_edit: dict[int, bool] = {}
        self._minimized_buttons: dict[int, QToolButton] = {}
        self._minimized_host_preferred_width = 420

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

        self.title_block = QWidget(self)
        self.title_block_layout = QHBoxLayout(self.title_block)
        self.title_block_layout.setContentsMargins(0, 0, 0, 0)
        self.title_block_layout.setSpacing(8)
        self.title_block_layout.addWidget(self.icon_label)
        self.title_block_layout.addWidget(self.title_label)

        self.minimized_host = QWidget(self)
        self.minimized_host.setObjectName("MinimizedDialogsHost")
        self.minimized_host.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.minimized_host.setFixedHeight(28)
        minimized_host_layout = QHBoxLayout(self.minimized_host)
        minimized_host_layout.setContentsMargins(0, 0, 0, 0)
        minimized_host_layout.setSpacing(4)

        self.minimized_left = QToolButton()
        self.minimized_left.setObjectName("MinimizedDialogsArrow")
        self.minimized_left.setText("◀")
        self.minimized_left.setFixedSize(20, 24)
        self.minimized_left.clicked.connect(lambda: self._scroll_minimized(-120))

        self.minimized_right = QToolButton()
        self.minimized_right.setObjectName("MinimizedDialogsArrow")
        self.minimized_right.setText("▶")
        self.minimized_right.setFixedSize(20, 24)
        self.minimized_right.clicked.connect(lambda: self._scroll_minimized(120))

        self.minimized_scroll = QScrollArea()
        self.minimized_scroll.setObjectName("MinimizedDialogsScroll")
        self.minimized_scroll.setWidgetResizable(True)
        self.minimized_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.minimized_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.minimized_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.minimized_scroll.setFixedHeight(28)
        self.minimized_scroll.setAutoFillBackground(False)
        self.minimized_scroll.viewport().setObjectName("MinimizedDialogsViewport")
        self.minimized_scroll.viewport().setAutoFillBackground(False)
        self.minimized_strip = QWidget()
        self.minimized_strip.setObjectName("MinimizedDialogsStrip")
        self.minimized_strip.setAutoFillBackground(False)
        self.minimized_strip_layout = QHBoxLayout(self.minimized_strip)
        self.minimized_strip_layout.setContentsMargins(5, 2, 5, 2)
        self.minimized_strip_layout.setSpacing(5)
        self.minimized_strip_layout.addStretch(1)
        self.minimized_strip_layout.addStretch(1)
        self.minimized_scroll.setWidget(self.minimized_strip)
        self.minimized_scroll.horizontalScrollBar().rangeChanged.connect(lambda *_: self._update_minimized_navigation())
        self.minimized_scroll.horizontalScrollBar().valueChanged.connect(lambda *_: self._update_minimized_navigation())

        minimized_host_layout.addWidget(self.minimized_left)
        minimized_host_layout.addWidget(self.minimized_scroll, 1)
        minimized_host_layout.addWidget(self.minimized_right)
        self.minimized_host.setVisible(False)

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

        self.window_controls = QWidget(self)
        self.window_controls_layout = QHBoxLayout(self.window_controls)
        self.window_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.window_controls_layout.setSpacing(0)
        self.window_controls_layout.addWidget(self.btn_min)
        self.window_controls_layout.addWidget(self.btn_max)
        self.window_controls_layout.addWidget(self.btn_close)

        layout.addWidget(self.title_block)
        layout.addStretch(1)
        layout.addWidget(self.window_controls)

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
            QWidget#MinimizedDialogsHost {{
                background: transparent;
            }}
            QScrollArea#MinimizedDialogsScroll {{
                background: transparent;
            }}
            QWidget#MinimizedDialogsViewport {{
                background: transparent;
            }}
            QWidget#MinimizedDialogsStrip {{
                background: transparent;
            }}
            QToolButton#MinimizedTaskChip {{
                color: #d8dbe7;
                background: #2a2d36;
                border: 1px solid #3a3f4b;
                border-radius: 7px;
                padding: 2px 8px;
                min-height: 22px;
            }}
            QToolButton#MinimizedTaskChip:hover {{
                background: #343a49;
            }}
            QToolButton#MinimizedDialogsArrow {{
                color: #cfcfcf;
                background: #262a34;
                border: 1px solid #3a3f4b;
                border-radius: 6px;
                font-size: 10px;
                padding: 0;
            }}
            QToolButton#MinimizedDialogsArrow:hover {{
                background: #303647;
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

    def register_minimized_task_dialog(
        self,
        dialog: QWidget,
        task_id: int,
        is_edit_dialog: bool,
        on_restore: Callable[[], None],
    ) -> None:
        key = id(dialog)
        if key in self._minimized_buttons:
            return
        chip = QToolButton(self.minimized_strip)
        chip.setObjectName("MinimizedTaskChip")
        chip.setCursor(Qt.CursorShape.PointingHandCursor)
        chip.setText(f"MN-{task_id}")
        chip.setToolTip("Восстановить окно задачи")
        chip.clicked.connect(on_restore)
        insert_index = max(0, self.minimized_strip_layout.count() - 1)
        self.minimized_strip_layout.insertWidget(insert_index, chip, 0, Qt.AlignmentFlag.AlignVCenter)
        self._minimized_restore_handlers[key] = on_restore
        self._minimized_is_edit[key] = bool(is_edit_dialog)
        self._minimized_buttons[key] = chip
        self.minimized_host.setVisible(True)
        QTimer.singleShot(0, self._update_minimized_host_layout)

    def unregister_minimized_task_dialog(self, dialog: QWidget) -> None:
        key = id(dialog)
        chip = self._minimized_buttons.pop(key, None)
        self._minimized_restore_handlers.pop(key, None)
        self._minimized_is_edit.pop(key, None)
        if chip is not None:
            self.minimized_strip_layout.removeWidget(chip)
            chip.deleteLater()
        if not self._minimized_buttons:
            self.minimized_host.setVisible(False)
        self._update_minimized_host_layout()

    def has_minimized_task_edit_dialogs(self) -> bool:
        return any(self._minimized_is_edit.values())

    def _scroll_minimized(self, delta: int) -> None:
        bar = self.minimized_scroll.horizontalScrollBar()
        bar.setValue(bar.value() + delta)
        self._update_minimized_navigation()

    def _update_minimized_navigation(self) -> None:
        if not self.minimized_host.isVisible():
            self.minimized_left.setVisible(False)
            self.minimized_right.setVisible(False)
            return
        bar = self.minimized_scroll.horizontalScrollBar()
        has_overflow = bar.maximum() > 0
        self.minimized_left.setVisible(has_overflow)
        self.minimized_right.setVisible(has_overflow)
        self.minimized_left.setEnabled(has_overflow and bar.value() > bar.minimum())
        self.minimized_right.setEnabled(has_overflow and bar.value() < bar.maximum())

    def _update_minimized_host_layout(self) -> None:
        if not self.minimized_host.isVisible():
            self.minimized_host.hide()
            self._update_minimized_navigation()
            return
        layout = self.layout()
        if layout is not None:
            layout.activate()
        margins = layout.contentsMargins() if layout is not None else None
        left_margin = margins.left() if margins is not None else 10
        right_margin = margins.right() if margins is not None else 10

        title_block_geometry = self.title_block.geometry()
        if title_block_geometry.width() > 0:
            left_edge = title_block_geometry.right() + 16
        else:
            left_edge = left_margin + self.title_block.sizeHint().width() + 16

        controls_geometry = self.window_controls.geometry()
        if controls_geometry.width() > 0:
            right_edge = controls_geometry.left() - 16
        else:
            right_edge = self.width() - right_margin - self.window_controls.sizeHint().width() - 16
        available_width = max(0, right_edge - left_edge)
        if available_width <= 0:
            self.minimized_host.hide()
            return

        preferred_width = min(
            max(220, self._minimized_host_preferred_width),
            available_width,
        )
        host_x = (self.width() - preferred_width) // 2
        if host_x < left_edge:
            host_x = left_edge
        if host_x + preferred_width > right_edge:
            host_x = max(left_edge, right_edge - preferred_width)

        host_y = (self.height() - self.minimized_host.height()) // 2
        self.minimized_host.setGeometry(host_x, host_y, preferred_width, self.minimized_host.height())
        self.minimized_host.raise_()
        self._update_minimized_navigation()

    def _toggle_max_restore(self):
        """Переключает окно между нормальным и развернутым состояниями."""
        if not self._window.isMaximized() and hasattr(self._window, "_restore_geom"):
            self._window._restore_geom = self._window.geometry()

        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

        self.sync_max_button()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_minimized_host_layout)

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
