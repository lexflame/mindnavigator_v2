from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QApplication,
    QSystemTrayIcon,
    QMenu,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QPoint, QRect, QEvent

from .windowing import ResizeEdge
from .ui.titlebar import TitleBar
from .ui.leftrail import LeftRail
from .ui.projects_nav import ProjectsNav
from .ui.search_nav import SearchNav
from .workspaces.tasks_workspace import TasksWorkspace
from .workspaces.projects_workspace import ProjectsWorkspace
from .workspaces.maps_workspace import MapsListWorkspace
from .workspaces.notes_workspace import NoteWorkspace
from .workspaces.settings_workspace import SettingsWorkspace
from .workspaces.files_workspace import FileWorkspace
from .workspaces.objects_workspace import ObjectWorkspace
from .constants import APP_NAME
from .resources import resource_path

from .ui.styles import TITLEBAR_BACKGROUND


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
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        self._resize_edge = ResizeEdge.NONE
        self._resizing = False
        self._press_global = QPoint()
        self._start_geom = QRect()

        self._restore_geom = QRect()
        self._tray_icon: QSystemTrayIcon | None = None
        self._was_maximized_before_minimize = False
        self._was_maximized_before_fullscreen = False
        self._map_fullscreen_active = False
        self._map_fullscreen_restore: dict[str, bool] = {}

        self._build_ui()
        self._wire_modes()
        self._init_tray()

        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.set_mode(self.MODE_TASKS)

    def _init_tray(self):
        """Настраивает системный трей для сворачивания приложения."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon = QIcon(resource_path("assets/icon.ico"))
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        action_show = menu.addAction("Показать")
        action_quit = menu.addAction("Выход")

        action_show.triggered.connect(self._restore_from_tray)
        action_quit.triggered.connect(QApplication.instance().quit)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Обрабатывает клики по иконке в трее."""
        if reason == QSystemTrayIcon.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        """Возвращает окно из трея."""
        if self.isHidden():
            if self._was_maximized_before_minimize:
                self.showMaximized()
            else:
                self.showNormal()
        self.raise_()
        self.activateWindow()
        self.title_bar.sync_max_button()

    def _minimize_to_tray(self):
        """Сворачивает окно в трей."""
        if self._tray_icon is None:
            return
        self.hide()
        self._tray_icon.showMessage(
            APP_NAME,
            "Приложение свернуто в трей.",
            QSystemTrayIcon.Information,
            2000,
        )

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
        self.title_bar.setStyleSheet(f"""
            QWidget#TitleBar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b3465, stop:0.5 #1b223a, stop:0.5001 #CCC, stop:1 #CCC);
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

        container_layout.addWidget(self.title_bar)

        body = QWidget()
        body.setObjectName("Body")
        container_layout.addWidget(body, 1)

        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.left_rail = LeftRail()
        body_layout.addWidget(self.left_rail)

        self.nav_column = QWidget()
        self.nav_column.setObjectName("NavColumn")
        nav_layout = QVBoxLayout(self.nav_column)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.projects_nav = ProjectsNav()
        self.search_nav = SearchNav()
        nav_layout.addWidget(self.projects_nav, 1)
        nav_layout.addWidget(self.search_nav, 0)

        body_layout.addWidget(self.nav_column)

        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        body_layout.addWidget(self.workspace_stack, 1)

        # Pages
        self.page_tasks = TasksWorkspace()
        self.page_projects = ProjectsWorkspace()
        self.page_maps = MapsListWorkspace()
        self.page_notes = NoteWorkspace()
        self.page_files = FileWorkspace()
        self.page_objects = ObjectWorkspace()
        self.page_settings = SettingsWorkspace()

        self._page_index = {
            self.MODE_PROJECTS: self.workspace_stack.addWidget(self.page_projects),
            self.MODE_TASKS: self.workspace_stack.addWidget(self.page_tasks),
            self.MODE_MAPS: self.workspace_stack.addWidget(self.page_maps),
            self.MODE_NOTES: self.workspace_stack.addWidget(self.page_notes),
            self.MODE_FILES: self.workspace_stack.addWidget(self.page_files),
            self.MODE_OBJECTS: self.workspace_stack.addWidget(self.page_objects),
            self.MODE_SETTINGS: self.workspace_stack.addWidget(self.page_settings),
        }

        self.projects_nav.filter_changed.connect(self._on_nav_filter_changed)
        self._current_mode = self.MODE_TASKS

        MATH_PHYS_PATTERN = (
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMjAiIGhlaWdodD0iMjIwIiB2aWV3Qm94PSIwIDAgMjIwIDIyMCI+CiAgPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDgiIHN0cm9rZS13aWR0aD0iMSI+CiAgICA8Y2lyY2xlIGN4PSI2MCIgY3k9IjYwIiByPSIyNiIvPgogICAgPGNpcmNsZSBjeD0iMTYwIiBjeT0iMTUwIiByPSIzMiIvPgogICAgPHBhdGggZD0iTTAgMTEwIFEgMzUgODAgNzAgMTEwIFQgMTQwIDExMCBUIDIyMCAxMTAiLz4KICAgIDxwYXRoIGQ9Ik0yMCAyMDAgTCAyMDAgMjAiLz4KICAgIDxwYXRoIGQ9Ik0zMCAyMCBMIDE5MCAxODAiLz4KICA8L2c+CiAgPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDYiIHN0cm9rZS13aWR0aD0iMSI+CiAgICA8cGF0aCBkPSJNMTEwIDAgTCAxMTAgMjIwIi8+CiAgICA8cGF0aCBkPSJNMCAxMTAgTCAyMjAgMTEwIi8+CiAgPC9nPgo8L3N2Zz4="
        )

        self.centralWidget().setStyleSheet(f"""
            QWidget#OuterRoot {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1c181b, stop:0.5 #101217, stop:0.6001 #101217, stop:1 #101217);
                background-image: url("{MATH_PHYS_PATTERN}");
                background-position: top left;
                background-repeat: repeat;
            }}
            QWidget#Container {{ border: 1px solid #2a2b2f; }}
        """)

        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())

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
        self._current_mode = mode_name
        self.projects_nav.set_mode_title(mode_name)
        self.workspace_stack.setCurrentIndex(self._page_index.get(mode_name, self._page_index[self.MODE_TASKS]))
        if mode_name == self.MODE_TASKS:
            self.page_tasks.refresh_tasks()
        elif mode_name == self.MODE_PROJECTS:
            self.page_projects.refresh_projects()
        elif mode_name == self.MODE_OBJECTS:
            self.page_objects.refresh_objects()

        for btn, m in self._btn_to_mode.items():
            if m == mode_name:
                btn.setChecked(True)
                break

    def _on_nav_filter_changed(self, kind: str, value: object) -> None:
        mode = self._current_mode
        if mode == self.MODE_TASKS:
            if kind == "project":
                self.page_tasks.set_project_filter(value["id"])
            elif kind == "clear":
                self.page_tasks.set_project_filter(None)
            return
        if mode == self.MODE_PROJECTS:
            if kind == "task":
                self.page_projects.set_task_filter(value["id"])
            elif kind == "clear":
                self.page_projects.set_task_filter(None)
            return
        if mode == self.MODE_FILES:
            if kind == "project":
                self.page_files.set_project_filter(value["id"])
            elif kind == "clear":
                self.page_files.set_project_filter(None)
            return
        if mode == self.MODE_MAPS:
            if kind == "project":
                self.page_maps.set_project_filter(value["title"])
            elif kind == "clear":
                self.page_maps.set_project_filter(None)
            return
        if mode == self.MODE_NOTES:
            if kind == "task":
                self.page_notes.set_task_filter(value["id"])
            elif kind == "map":
                project = value.get("project") or None
                self.page_notes.set_project_filter(project)
            elif kind == "clear":
                self.page_notes.set_project_filter(None)
                self.page_notes.set_task_filter(None)
            return
        if mode == self.MODE_OBJECTS:
            if kind == "project":
                self.page_objects.set_project_filter(value["id"])
            elif kind == "task":
                self.page_objects.set_task_filter(value["id"])
            elif kind == "marker":
                self.page_objects.set_marker_filter(value["id"])
            elif kind == "clear":
                self.page_objects.set_project_filter(None)
                self.page_objects.set_task_filter(None)
                self.page_objects.set_marker_filter(None)

    def resizeEvent(self, event):
        """Обрабатывает ресайз окна, синхронизируя ширину навигации."""
        super().resizeEvent(event)
        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())

    def changeEvent(self, event):
        """Обрабатывает сворачивание окна для отправки в трей."""
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self._was_maximized_before_minimize = bool(event.oldState() & Qt.WindowMaximized)
            self._minimize_to_tray()

    def keyPressEvent(self, event):
        """Обрабатывает горячие клавиши окна."""
        if event.key() == Qt.Key_Escape and self._map_fullscreen_active:
            self.set_map_fullscreen(False)
            event.accept()
            return
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                if self._was_maximized_before_fullscreen:
                    self.showMaximized()
                else:
                    self.showNormal()
                self.title_bar.sync_max_button()
            else:
                self._was_maximized_before_fullscreen = self.isMaximized()
                self.showFullScreen()
            event.accept()
            return
        super().keyPressEvent(event)

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

    def set_map_fullscreen(self, enabled: bool) -> None:
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        if enabled:
            self._map_fullscreen_restore = {
                "title_bar": self.title_bar.isVisible(),
                "left_rail": self.left_rail.isVisible(),
                "nav_column": self.nav_column.isVisible(),
            }
            self._was_maximized_before_fullscreen = self.isMaximized()
            self.title_bar.setVisible(False)
            self.left_rail.setVisible(False)
            self.nav_column.setVisible(False)
            self.showFullScreen()
        else:
            self.title_bar.setVisible(self._map_fullscreen_restore.get("title_bar", True))
            self.left_rail.setVisible(self._map_fullscreen_restore.get("left_rail", True))
            self.nav_column.setVisible(self._map_fullscreen_restore.get("nav_column", True))
            if self._was_maximized_before_fullscreen:
                self.showMaximized()
            else:
                self.showNormal()
            self.title_bar.sync_max_button()
        self.page_maps.set_map_fullscreen_state(enabled)
