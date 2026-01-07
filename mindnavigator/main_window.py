from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QPoint, QRect

from .windowing import ResizeEdge
from .ui.titlebar import TitleBar
from .ui.leftrail import LeftRail
from .ui.projects_nav import ProjectsNav
from .workspaces.tasks_workspace import TasksWorkspace
from .workspaces.projects_workspace import ProjectsWorkspace
from .constants import APP_NAME


class MainWindow(QMainWindow):
    """Главное окно приложения с кастомным заголовком и рабочими областями."""

    RESIZE_MARGIN = 7
    SNAP_THRESHOLD = 14

    MODE_PROJECTS = "Проекты"
    MODE_TASKS = "Задачи"
    MODE_MAPS = "Карты"
    MODE_NOTES = "Заметки"
    MODE_FILES = "Файлы"
    MODE_OBJECTS = "Объекты"
    MODE_SETTINGS = "Настройки"

    def __init__(self):
        """Инициализирует окно, компоненты интерфейса и обработчики."""
        super().__init__()

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self.setMinimumSize(1100, 700)
        self.setWindowIcon(QIcon("assets/icon.png"))

        self._resize_edge = ResizeEdge.NONE
        self._resizing = False
        self._press_global = QPoint()
        self._start_geom = QRect()

        self._restore_geom = QRect()

        self._build_ui()
        self._wire_modes()

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.set_mode(self.MODE_TASKS)

    def _build_ui(self):
        """Создает и компонует основные виджеты окна."""
        outer = QWidget(self)
        outer.setObjectName("OuterRoot")
        self.setCentralWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.container = QWidget()
        self.container.setObjectName("Container")
        outer_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        container_layout.addWidget(self.title_bar)

        body = QWidget()
        body.setObjectName("Body")
        container_layout.addWidget(body, 1)

        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.left_rail = LeftRail()
        body_layout.addWidget(self.left_rail)

        self.projects_nav = ProjectsNav()
        body_layout.addWidget(self.projects_nav)

        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        body_layout.addWidget(self.workspace_stack, 1)

        # Pages
        self.page_tasks = TasksWorkspace()
        self.page_projects = ProjectsWorkspace()
        self.page_maps = self._placeholder("Карты", "Рабочая область режима «Карты».")
        self.page_notes = self._placeholder("Заметки", "Рабочая область режима «Заметки».")
        self.page_files = self._placeholder("Файлы", "Рабочая область режима «Файлы».")
        self.page_objects = self._placeholder("Объекты", "Рабочая область режима «Объекты».")
        self.page_settings = self._placeholder("Настройки", "Рабочая область режима «Настройки».")

        self._page_index = {
            self.MODE_PROJECTS: self.workspace_stack.addWidget(self.page_projects),
            self.MODE_TASKS: self.workspace_stack.addWidget(self.page_tasks),
            self.MODE_MAPS: self.workspace_stack.addWidget(self.page_maps),
            self.MODE_NOTES: self.workspace_stack.addWidget(self.page_notes),
            self.MODE_FILES: self.workspace_stack.addWidget(self.page_files),
            self.MODE_OBJECTS: self.workspace_stack.addWidget(self.page_objects),
            self.MODE_SETTINGS: self.workspace_stack.addWidget(self.page_settings),
        }

        self.centralWidget().setStyleSheet("""
            QWidget#OuterRoot { background: #16171a; }
            QWidget#Container { background: #16171a; border: 1px solid #2a2b2f; }
        """)

        self.projects_nav.update_width_for_window(self.width())

    def _placeholder(self, title: str, subtitle: str) -> QWidget:
        """Возвращает временный экран-заглушку для неготовых режимов."""
        w = QWidget()
        w.setObjectName("Placeholder")
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#cfcfcf; font-size:22px;")
        s = QLabel(subtitle)
        s.setStyleSheet("color:#7a7a7a; font-size:13px;")
        s.setWordWrap(True)
        s.setMaximumWidth(640)
        s.setAlignment(Qt.AlignCenter)
        l.addWidget(t)
        l.addWidget(s)
        w.setStyleSheet("QWidget#Placeholder { background: #16171a; }")
        return w

    def _wire_modes(self):
        """Связывает кнопки левого меню с режимами рабочих областей."""
        self._btn_to_mode = {
            self.left_rail.btn_projects: self.MODE_PROJECTS,
            self.left_rail.btn_tasks: self.MODE_TASKS,
            self.left_rail.btn_maps: self.MODE_MAPS,
            self.left_rail.btn_notes: self.MODE_NOTES,
            self.left_rail.btn_files: self.MODE_FILES,
            self.left_rail.btn_objects: self.MODE_OBJECTS,
            self.left_rail.btn_settings: self.MODE_SETTINGS,
        }
        for btn, mode in self._btn_to_mode.items():
            btn.clicked.connect(lambda checked=False, m=mode: self.set_mode(m))

    def set_mode(self, mode_name: str):
        """Переключает активную рабочую область и обновляет заголовки."""
        self.title_bar.title_label.setText(f"{APP_NAME} · {mode_name}")
        self.projects_nav.set_mode_title(mode_name)
        self.workspace_stack.setCurrentIndex(self._page_index.get(mode_name, self._page_index[self.MODE_TASKS]))

        for btn, m in self._btn_to_mode.items():
            if m == mode_name:
                btn.setChecked(True)
                break

    def resizeEvent(self, event):
        """Обрабатывает ресайз окна, синхронизируя ширину навигации."""
        super().resizeEvent(event)
        self.projects_nav.update_width_for_window(self.width())

    # ----- Snap / detach -----
    def _snap_to_screen_edges(self, global_pos: QPoint):
        """Прилипает окно к краям экрана и разворачивает при касании верхней границы."""
        if self.isMaximized():
            return

        screen = QApplication.screenAt(global_pos) or self.screen()
        geo = screen.availableGeometry()
        t = self.SNAP_THRESHOLD
        x, y = global_pos.x(), global_pos.y()

        if abs(y - geo.top()) <= t:
            if self._restore_geom.isNull():
                self._restore_geom = self.geometry()
            self.showMaximized()
            self.title_bar.sync_max_button()
            return

        if abs(x - geo.left()) <= t:
            self.setGeometry(QRect(geo.left(), geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

        if abs(x - geo.right()) <= t:
            self.setGeometry(QRect(geo.left() + geo.width() // 2, geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

    def _begin_restore_on_drag(self, global_pos: QPoint):
        """Восстанавливает нормальный размер при перетаскивании из maximize."""
        if not self.isMaximized():
            return

        if self._restore_geom.isNull():
            self._restore_geom = self.normalGeometry()

        screen = QApplication.screenAt(global_pos) or self.screen()
        avail = screen.availableGeometry()
        rel_x = (global_pos.x() - avail.left()) / max(1, avail.width())
        rel_x = min(max(rel_x, 0.05), 0.95)

        self.showNormal()
        self.title_bar.sync_max_button()

        w = self._restore_geom.width() if self._restore_geom.width() > 0 else 1100
        h = self._restore_geom.height() if self._restore_geom.height() > 0 else 700

        new_x = int(global_pos.x() - w * rel_x)
        new_y = int(global_pos.y() - self.title_bar.HEIGHT / 2)

        self.setGeometry(new_x, new_y, w, h)
        self._restore_geom = self.geometry()

    # ----- Resize -----
    def _hit_test_edges(self, pos: QPoint) -> ResizeEdge:
        """Определяет, за какой край окна отвечает текущая позиция мыши."""
        if self.isMaximized():
            return ResizeEdge.NONE

        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self.RESIZE_MARGIN

        edge = ResizeEdge.NONE
        if x <= m:
            edge |= ResizeEdge.LEFT
        elif x >= w - m:
            edge |= ResizeEdge.RIGHT

        if y <= m:
            edge |= ResizeEdge.TOP
        elif y >= h - m:
            edge |= ResizeEdge.BOTTOM

        return edge

    def _cursor_for_edge(self, edge: ResizeEdge):
        """Возвращает подходящий курсор для выбранного края."""
        if edge in (ResizeEdge.LEFT, ResizeEdge.RIGHT):
            return Qt.SizeHorCursor
        if edge in (ResizeEdge.TOP, ResizeEdge.BOTTOM):
            return Qt.SizeVerCursor
        if edge in (ResizeEdge.TOP | ResizeEdge.LEFT, ResizeEdge.BOTTOM | ResizeEdge.RIGHT):
            return Qt.SizeFDiagCursor
        if edge in (ResizeEdge.TOP | ResizeEdge.RIGHT, ResizeEdge.BOTTOM | ResizeEdge.LEFT):
            return Qt.SizeBDiagCursor
        return Qt.ArrowCursor

    def _start_resize(self, edge: ResizeEdge, global_pos: QPoint):
        """Стартует операцию изменения размеров окна."""
        self._resizing = True
        self._resize_edge = edge
        self._press_global = global_pos
        self._start_geom = self.geometry()

    def _do_resize(self, global_pos: QPoint):
        """Выполняет изменение геометрии окна во время ресайза."""
        if not self._resizing or self._resize_edge == ResizeEdge.NONE:
            return

        dx = global_pos.x() - self._press_global.x()
        dy = global_pos.y() - self._press_global.y()

        g = QRect(self._start_geom)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        if self._resize_edge & ResizeEdge.LEFT:
            new_x = g.x() + dx
            new_w = g.width() - dx
            if new_w >= min_w:
                g.setX(new_x)
                g.setWidth(new_w)

        if self._resize_edge & ResizeEdge.RIGHT:
            new_w = g.width() + dx
            if new_w >= min_w:
                g.setWidth(new_w)

        if self._resize_edge & ResizeEdge.TOP:
            new_y = g.y() + dy
            new_h = g.height() - dy
            if new_h >= min_h:
                g.setY(new_y)
                g.setHeight(new_h)

        if self._resize_edge & ResizeEdge.BOTTOM:
            new_h = g.height() + dy
            if new_h >= min_h:
                g.setHeight(new_h)

        self.setGeometry(g)
        self._restore_geom = self.geometry()

    def _stop_resize(self):
        """Сбрасывает состояние изменения размеров."""
        self._resizing = False
        self._resize_edge = ResizeEdge.NONE

    def eventFilter(self, obj, event):
        """Перехватывает события мыши для кастомного ресайза."""
        if obj is self:
            # 🔥 В maximized полностью выключаем hit-test и дергание курсора
            if self.isMaximized():
                if event.type() in (event.Type.MouseMove, event.Type.Leave):
                    self.unsetCursor()
                return super().eventFilter(obj, event)

            if event.type() == event.Type.MouseMove:
                pos = event.position().toPoint()
                global_pos = event.globalPosition().toPoint()

                if self._resizing:
                    self._do_resize(global_pos)
                    return True

                edge = self._hit_test_edges(pos)
                if edge != self._resize_edge:
                    self._resize_edge = edge
                    self.setCursor(self._cursor_for_edge(edge))
                return False

            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    pos = event.position().toPoint()
                    edge = self._hit_test_edges(pos)
                    if edge != ResizeEdge.NONE:
                        self._start_resize(edge, event.globalPosition().toPoint())
                        return True
                return False

            if event.type() == event.Type.MouseButtonRelease:
                if self._resizing:
                    self._stop_resize()
                    return True
                return False

            if event.type() == event.Type.Leave:
                if not self._resizing:
                    self.unsetCursor()
                return False

        return super().eventFilter(obj, event)
