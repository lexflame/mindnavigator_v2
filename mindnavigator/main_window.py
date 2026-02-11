"""Главное окно приложения и связанная логика интерфейса.

Входные данные:
    События Qt, пользовательские действия и данные из рабочих областей.

Выходные данные:
    Отрисованные виджеты и изменения состояния интерфейса.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QStackedWidget,
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QPoint, QRect, QEvent
from pathlib import Path

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
from .ui.workspaces.collections_workspace import CollectionsWorkspace
from .workspaces.files_workspace import FileWorkspace
from .workspaces.objects_workspace import ObjectWorkspace
from .workspaces.ideas_workspace import IdeasWorkspace
from .constants import APP_NAME
from .resources import resource_path
from .hotkeys import HotkeyEventFilter, HotkeyManager, HotkeyOverridesStore, load_commands_from_json

from .ui.styles import MATH_PHYS_PATTERN, TITLEBAR_BACKGROUND


class MainWindow(QMainWindow):
    """Главное окно приложения с кастомным заголовком и рабочими областями."""

    RESIZE_MARGIN = 7
    SNAP_THRESHOLD = 14

    MODE_PROJECTS = "Проекты"
    MODE_TASKS = "Задачи"
    MODE_IDEAS = "Идеи"
    MODE_MAPS = "Карты"
    MODE_NOTES = "Заметки"
    MODE_FILES = "Файлы"
    MODE_COLLECTIONS = "Коллекции"
    MODE_OBJECTS = "Объекты"
    MODE_SETTINGS = "Настройки"

    def __init__(self):
        """Инициализирует окно, компоненты интерфейса и обработчики."""
        super().__init__()

        # Настраиваем базовые флаги окна и прозрачность.
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Включаем автозаливку, чтобы корректно рисовать фон.
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        # Определяем минимальные размеры и иконку приложения.
        self.setMinimumSize(1100, 700)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # Инициализируем состояние кастомного ресайза.
        self._resize_edge = ResizeEdge.NONE
        self._resizing = False
        self._press_global = QPoint()
        self._start_geom = QRect()

        # Инициализируем состояние трея, полноэкранного режима карты и восстановления геометрии.
        self._restore_geom = QRect()
        self._tray_icon: QSystemTrayIcon | None = None
        self._was_maximized_before_minimize = False
        self._was_maximized_before_fullscreen = False
        self._map_fullscreen_active = False
        self._map_fullscreen_restore: dict[str, bool] = {}

        # Собираем интерфейс, связываем режимы и инициализируем трей.
        self._build_ui()
        self._wire_modes()
        self._init_tray()
        self._init_hotkeys()

        # Включаем отслеживание мыши и фильтр событий для собственного ресайза.
        self.setMouseTracking(True)
        self.installEventFilter(self)

        # Выставляем стартовый режим.
        self.set_mode(self.MODE_TASKS)

    def _init_tray(self):
        """Настраивает системный трей для сворачивания приложения."""
        # Проверяем, доступен ли системный трей.
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        # Создаем иконку трея и контекстное меню.
        icon = QIcon(resource_path("assets/icon.ico"))
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        action_show = menu.addAction("Показать")
        action_quit = menu.addAction("Выход")

        # Связываем действия меню.
        action_show.triggered.connect(self._restore_from_tray)
        action_quit.triggered.connect(QApplication.instance().quit)

        # Подключаем меню и обработчик кликов по иконке.
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Обрабатывает клики по иконке в трее."""
        # На одиночный клик восстанавливаем окно.
        if reason == QSystemTrayIcon.Trigger:
            self._restore_from_tray()

    def _restore_from_tray(self):
        """Возвращает окно из трея."""
        # Восстанавливаем режим отображения до сворачивания.
        if self.isHidden():
            if self._was_maximized_before_minimize:
                self.showMaximized()
            else:
                self.showNormal()
        # Поднимаем окно поверх и синхронизируем состояние кнопки.
        self.raise_()
        self.activateWindow()
        self.title_bar.sync_max_button()

    def _minimize_to_tray(self):
        """Сворачивает окно в трей."""
        # Если трей не создан, выходим без действий.
        if self._tray_icon is None:
            return
        # Прячем окно и показываем уведомление.
        self.hide()
        self._tray_icon.showMessage(
            APP_NAME,
            "Приложение свернуто в трей.",
            QSystemTrayIcon.Information,
            2000,
        )

    def _hotkey_defaults_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "defaults" / "hotkeys.default.json"

    def _hotkey_overrides_path(self) -> Path:
        return Path.home() / ".mindnavigator" / "hotkeys.overrides.json"

    def _init_hotkeys(self) -> None:
        commands = load_commands_from_json(self._hotkey_defaults_path())
        self.hotkeys = HotkeyManager(commands)
        self.hotkey_store = HotkeyOverridesStore(self._hotkey_overrides_path())
        self.hotkey_store.apply(self.hotkeys)
        self._hotkey_callbacks = {
            "task.create": self._hotkey_create_task,
            "app.tray.minimize": self._minimize_to_tray,
            "app.tray.restore": self._restore_from_tray,
            "nav.workspace.next": lambda: self._cycle_workspace(+1),
            "nav.workspace.prev": lambda: self._cycle_workspace(-1),
            "nav.sheet.next": lambda: self._cycle_entity_sheet(+1),
            "nav.sheet.prev": lambda: self._cycle_entity_sheet(-1),
            "ui.command_palette": self._show_command_palette,
            "ui.settings.open": lambda: self.set_mode(self.MODE_SETTINGS),
            "ui.hotkeys.help": self._show_hotkeys_help,
        }
        self._hotkey_filter = HotkeyEventFilter(self.hotkeys, self._resolve_hotkey_callback, self)
        QApplication.instance().installEventFilter(self._hotkey_filter)
        self._update_hotkey_contexts()

    def _resolve_hotkey_callback(self, command_id: str):
        return self._hotkey_callbacks.get(command_id)

    def _update_hotkey_contexts(self) -> None:
        contexts = ["Global", f"Workspace:{self._workspace_context_name()}"]
        if QApplication.activeModalWidget() is not None:
            contexts.append("ModalOnly")
        self.hotkeys.set_active_contexts(contexts)

    def _workspace_context_name(self) -> str:
        mapping = {
            self.MODE_TASKS: "Tasks",
            self.MODE_PROJECTS: "Projects",
            self.MODE_IDEAS: "Ideas",
            self.MODE_MAPS: "Maps",
            self.MODE_NOTES: "Notes",
            self.MODE_FILES: "Files",
            self.MODE_COLLECTIONS: "Collections",
            self.MODE_OBJECTS: "Objects",
            self.MODE_SETTINGS: "Settings",
        }
        return mapping.get(self._current_mode, "Tasks")

    def _cycle_workspace(self, direction: int) -> None:
        modes = list(self._page_index.keys())
        current_idx = modes.index(self._current_mode)
        next_idx = (current_idx + direction) % len(modes)
        self.set_mode(modes[next_idx])

    def _cycle_entity_sheet(self, direction: int) -> None:
        workspace = self.workspace_stack.currentWidget()
        if workspace is None:
            return
        if direction > 0 and hasattr(workspace, "_show_next"):
            workspace._show_next()
        elif direction < 0 and hasattr(workspace, "_show_previous"):
            workspace._show_previous()

    def _hotkey_create_task(self) -> None:
        self.set_mode(self.MODE_TASKS)
        if hasattr(self.page_tasks, "new_title"):
            self.page_tasks.new_title.setFocus()

    def _show_hotkeys_help(self) -> None:
        self._update_hotkey_contexts()
        lines = []
        for command, binding in self.hotkeys.get_active_hotkeys():
            lines.append(f"{binding.sequence} — {command.title}")
        QMessageBox.information(self, "Горячие клавиши", "\n".join(lines) or "Нет доступных горячих клавиш")

    def _show_command_palette(self) -> None:
        self._update_hotkey_contexts()
        commands = sorted(self.hotkeys.get_active_hotkeys(), key=lambda item: item[0].title.lower())
        lines = [f"{command.title} ({binding.sequence})" for command, binding in commands]
        QMessageBox.information(self, "Command Palette", "\n".join(lines) or "Нет доступных команд")

    def _build_ui(self):
        """Создает и компонует основные виджеты окна."""
        # Корневой контейнер окна.
        outer = QWidget(self)
        outer.setObjectName("OuterRoot")
        self.setCentralWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Контейнер под заголовок и тело.
        self.container = QWidget()
        self.container.setObjectName("Container")
        outer_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Верхняя панель заголовка.
        self.title_bar = TitleBar(self)
        self._apply_titlebar_style()

        container_layout.addWidget(self.title_bar)

        # Основное тело окна.
        body = QWidget()
        body.setObjectName("Body")
        container_layout.addWidget(body, 1)

        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Левый rail с кнопками режимов.
        self.left_rail = LeftRail()
        body_layout.addWidget(self.left_rail)

        # Контейнер кнопки сворачивания навигации.
        self.nav_toggle_container = QWidget()
        self.nav_toggle_container.setObjectName("NavToggleContainer")
        nav_toggle_layout = QVBoxLayout(self.nav_toggle_container)
        nav_toggle_layout.setContentsMargins(0, 0, 0, 0)
        nav_toggle_layout.setSpacing(0)

        # Кнопка сворачивания/разворачивания.
        self.nav_toggle = QToolButton()
        self.nav_toggle.setObjectName("NavToggleButton")
        self.nav_toggle.setText("⟨")
        self.nav_toggle.setCursor(Qt.PointingHandCursor)
        self.nav_toggle.setToolTip("Свернуть навигацию")

        nav_toggle_layout.addStretch(1)
        nav_toggle_layout.addWidget(self.nav_toggle)
        nav_toggle_layout.addStretch(1)

        body_layout.addWidget(self.nav_toggle_container)

        # Колонка навигации и поиска.
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

        # Стек рабочих областей.
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        body_layout.addWidget(self.workspace_stack, 1)

        # Pages
        self.page_tasks = TasksWorkspace()
        self.page_projects = ProjectsWorkspace()
        self.page_ideas = IdeasWorkspace()
        self.page_maps = MapsListWorkspace()
        self.page_notes = NoteWorkspace()
        self.page_files = FileWorkspace()
        self.page_collections = CollectionsWorkspace()
        self.page_objects = ObjectWorkspace()
        self.page_settings = SettingsWorkspace()

        # Регистрируем страницы и сохраняем их индексы.
        self._page_index = {
            self.MODE_PROJECTS: self.workspace_stack.addWidget(self.page_projects),
            self.MODE_TASKS: self.workspace_stack.addWidget(self.page_tasks),
            self.MODE_IDEAS: self.workspace_stack.addWidget(self.page_ideas),
            self.MODE_MAPS: self.workspace_stack.addWidget(self.page_maps),
            self.MODE_NOTES: self.workspace_stack.addWidget(self.page_notes),
            self.MODE_FILES: self.workspace_stack.addWidget(self.page_files),
            self.MODE_COLLECTIONS: self.workspace_stack.addWidget(self.page_collections),
            self.MODE_OBJECTS: self.workspace_stack.addWidget(self.page_objects),
            self.MODE_SETTINGS: self.workspace_stack.addWidget(self.page_settings),
        }

        # Подключаем сигналы от навигации и поиска.
        self.projects_nav.filter_changed.connect(self._on_nav_filter_changed)
        self.search_nav.resultActivated.connect(self._on_search_result_activated)
        self._current_mode = self.MODE_TASKS

        # Кнопка сворачивания навигации.
        self.nav_toggle.clicked.connect(self._toggle_nav_column)

        # Применяем стили и синхронизацию размеров.
        self._apply_root_style()

        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())
        self._set_nav_collapsed(False)

    def _placeholder(self, title: str, subtitle: str) -> QWidget:
        """Возвращает временный экран-заглушку для неготовых режимов."""
        # Заглушка для режимов без реализации.
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

    def _apply_titlebar_style(self) -> None:
        """Применяет стили к заголовку окна."""
        # Устанавливаем стили для заголовка и кнопок управления.
        self.title_bar.setStyleSheet(f"""
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

    def _apply_root_style(self) -> None:
        """Применяет базовые стили к корневому контейнеру."""
        # Прописываем стили для фона, контейнера и кнопки навигации.
        self.centralWidget().setStyleSheet(f"""
            QWidget#OuterRoot {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1c181b, stop:0.5 #101217, stop:0.6001 #101217, stop:1 #101217);
                background-image: url("{MATH_PHYS_PATTERN}");
                background-position: top left;
                background-repeat: repeat;
            }}
            QWidget#Container {{ border: 1px solid #2a2b2f; }}
            QWidget#NavToggleContainer {{
                background: #1e1f22;
                border-right: 1px solid #2a2b2f;
            }}
            QToolButton#NavToggleButton {{
                background: transparent;
                border: none;
                color: #cfcfcf;
                font-size: 16px;
                padding: 4px 2px;
            }}
            QToolButton#NavToggleButton:hover {{
                background: #2a2b2f;
            }}
        """)

    def _apply_nav_state_to_workspace(self, workspace: QWidget) -> None:
        # Передаем активное состояние навигации в рабочие области.
        if hasattr(workspace, "set_nav_collapsed_state"):
            workspace.set_nav_collapsed_state(not self.nav_column.isVisible())

    def _set_nav_collapsed(self, collapsed: bool) -> None:
        # Скрываем/показываем колонку навигации и меняем подсказки.
        self.nav_column.setVisible(not collapsed)
        self.nav_toggle.setText("⟩" if collapsed else "⟨")
        self.nav_toggle.setToolTip("Развернуть навигацию" if collapsed else "Свернуть навигацию")
        self._apply_nav_state_to_workspace(self.workspace_stack.currentWidget())

    def _toggle_nav_column(self) -> None:
        # Переключаем состояние колонки навигации.
        self._set_nav_collapsed(self.nav_column.isVisible())

    def _wire_modes(self):
        """Связывает кнопки левого меню с режимами рабочих областей."""
        # Формируем соответствие кнопок и режимов.
        self._btn_to_mode = {
            self.left_rail.btn_projects: self.MODE_PROJECTS,
            self.left_rail.btn_tasks: self.MODE_TASKS,
            self.left_rail.btn_ideas: self.MODE_IDEAS,
            self.left_rail.btn_maps: self.MODE_MAPS,
            self.left_rail.btn_notes: self.MODE_NOTES,
            self.left_rail.btn_files: self.MODE_FILES,
            self.left_rail.btn_collections: self.MODE_COLLECTIONS,
            self.left_rail.btn_objects: self.MODE_OBJECTS,
            self.left_rail.btn_settings: self.MODE_SETTINGS,
        }
        # Подключаем клики на кнопки к смене режима.
        for btn, mode in self._btn_to_mode.items():
            btn.clicked.connect(lambda checked=False, m=mode: self.set_mode(m))

    def set_mode(self, mode_name: str):
        """Переключает активную рабочую область и обновляет заголовки."""
        # Обновляем заголовок окна и состояние навигации.
        self.title_bar.title_label.setText(f"{APP_NAME} · {mode_name}")
        previous_workspace = self.workspace_stack.currentWidget()
        if previous_workspace is not None and hasattr(previous_workspace, "on_leave"):
            previous_workspace.on_leave()
        self._current_mode = mode_name
        self.projects_nav.set_mode_title(mode_name)
        # Переключаем страницу в стеке.
        self.workspace_stack.setCurrentIndex(self._page_index.get(mode_name, self._page_index[self.MODE_TASKS]))
        self._apply_nav_state_to_workspace(self.workspace_stack.currentWidget())
        current_workspace = self.workspace_stack.currentWidget()
        if current_workspace is not None and hasattr(current_workspace, "on_enter"):
            current_workspace.on_enter(None)
        # Обновляем данные активной страницы.
        if mode_name == self.MODE_TASKS:
            self.page_tasks.refresh_tasks()
        elif mode_name == self.MODE_IDEAS:
            self.page_ideas.refresh()
        elif mode_name == self.MODE_PROJECTS:
            self.page_projects.refresh_projects()
        elif mode_name == self.MODE_OBJECTS:
            self.page_objects.refresh_objects()

        # Отмечаем выбранную кнопку в меню.
        for btn, m in self._btn_to_mode.items():
            if m == mode_name:
                btn.setChecked(True)
                break

        self._update_hotkey_contexts()

    def _on_nav_filter_changed(self, kind: str, value: object) -> None:
        # Определяем активный режим и прокидываем фильтры в соответствующий вид.
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
            return

    def _on_search_result_activated(self, payload: dict) -> None:
        # По типу найденной сущности переключаем нужный режим.
        entity = payload.get("entity")
        if entity == "task":
            self.set_mode(self.MODE_TASKS)
        elif entity == "project":
            self.set_mode(self.MODE_PROJECTS)
        elif entity == "map" or entity == "marker":
            self.set_mode(self.MODE_MAPS)
        elif entity == "note":
            self.set_mode(self.MODE_NOTES)
        elif entity == "file":
            self.set_mode(self.MODE_FILES)
        elif entity == "object":
            self.set_mode(self.MODE_OBJECTS)

    def resizeEvent(self, event):
        """Обрабатывает ресайз окна, синхронизируя ширину навигации."""
        # Передаем событие базовому классу и обновляем ширину панелей.
        super().resizeEvent(event)
        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())

    def closeEvent(self, event):
        if hasattr(self, "hotkey_store") and hasattr(self, "hotkeys"):
            self.hotkey_store.save(self.hotkeys)
        super().closeEvent(event)

    def changeEvent(self, event):
        """Обрабатывает сворачивание окна для отправки в трей."""
        # Отслеживаем сворачивание и отправляем окно в трей.
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self._was_maximized_before_minimize = bool(event.oldState() & Qt.WindowMaximized)
            self._minimize_to_tray()

    def keyPressEvent(self, event):
        """Обрабатывает горячие клавиши окна."""
        # Esc закрывает полноэкранный режим карты.
        if event.key() == Qt.Key_Escape and self._map_fullscreen_active:
            self.set_map_fullscreen(False)
            event.accept()
            return
        # F11 переключает полноэкранный режим окна.
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
        # В maximized режим прилипание не нужно.
        if self.isMaximized():
            return

        # Получаем активный экран и доступную геометрию.
        screen = QApplication.screenAt(global_pos) or self.screen()
        geo = screen.availableGeometry()
        t = self.SNAP_THRESHOLD
        x, y = global_pos.x(), global_pos.y()

        # Прикосновение к верхнему краю — разворачиваем окно.
        if abs(y - geo.top()) <= t:
            if self._restore_geom.isNull():
                self._restore_geom = self.geometry()
            self.showMaximized()
            self.title_bar.sync_max_button()
            return

        # Прикосновение к левому краю — половинное окно слева.
        if abs(x - geo.left()) <= t:
            self.setGeometry(QRect(geo.left(), geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

        # Прикосновение к правому краю — половинное окно справа.
        if abs(x - geo.right()) <= t:
            self.setGeometry(QRect(geo.left() + geo.width() // 2, geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

    def _begin_restore_on_drag(self, global_pos: QPoint):
        """Восстанавливает нормальный размер при перетаскивании из maximize."""
        # Если не maximized, ничего не делаем.
        if not self.isMaximized():
            return

        # Запоминаем геометрию окна до maximized.
        if self._restore_geom.isNull():
            self._restore_geom = self.normalGeometry()

        # Рассчитываем относительную позицию курсора по экрану.
        screen = QApplication.screenAt(global_pos) or self.screen()
        avail = screen.availableGeometry()
        rel_x = (global_pos.x() - avail.left()) / max(1, avail.width())
        rel_x = min(max(rel_x, 0.05), 0.95)

        # Восстанавливаем окно и пересчитываем геометрию под курсором.
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
        # В maximized режиме ресайз отключен.
        if self.isMaximized():
            return ResizeEdge.NONE

        # Определяем направление ресайза по координатам.
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
        # Подбираем курсор для направления ресайза.
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
        # Сохраняем параметры старта ресайза.
        self._resizing = True
        self._resize_edge = edge
        self._press_global = global_pos
        self._start_geom = self.geometry()

    def _do_resize(self, global_pos: QPoint):
        """Выполняет изменение геометрии окна во время ресайза."""
        # Если ресайз не активен, ничего не делаем.
        if not self._resizing or self._resize_edge == ResizeEdge.NONE:
            return

        # Рассчитываем смещения курсора.
        dx = global_pos.x() - self._press_global.x()
        dy = global_pos.y() - self._press_global.y()

        g = QRect(self._start_geom)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        # Обновляем границы в зависимости от направления ресайза.
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

        # Применяем новую геометрию и запоминаем ее.
        self.setGeometry(g)
        self._restore_geom = self.geometry()

    def _stop_resize(self):
        """Сбрасывает состояние изменения размеров."""
        # Сбрасываем флаги ресайза.
        self._resizing = False
        self._resize_edge = ResizeEdge.NONE

    def eventFilter(self, obj, event):
        """Перехватывает события мыши для кастомного ресайза."""
        # Обрабатываем события только для самого окна.
        if obj is self:
            # 🔥 В maximized полностью выключаем hit-test и дергание курсора
            if self.isMaximized():
                if event.type() in (event.Type.MouseMove, event.Type.Leave):
                    self.unsetCursor()
                return super().eventFilter(obj, event)

            if event.type() == event.Type.MouseMove:
                pos = event.position().toPoint()
                global_pos = event.globalPosition().toPoint()

                # Во время ресайза меняем геометрию.
                if self._resizing:
                    self._do_resize(global_pos)
                    return True

                # Обновляем курсор, если изменился край ресайза.
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
                        # Запускаем ресайз при нажатии на край.
                        self._start_resize(edge, event.globalPosition().toPoint())
                        return True
                return False

            if event.type() == event.Type.MouseButtonRelease:
                # Останавливаем ресайз по отпусканию.
                if self._resizing:
                    self._stop_resize()
                    return True
                return False

            if event.type() == event.Type.Leave:
                # Возвращаем курсор, если не ресайзим.
                if not self._resizing:
                    self.unsetCursor()
                return False

        return super().eventFilter(obj, event)

    def set_map_fullscreen(self, enabled: bool) -> None:
        # Не выполняем действия, если состояние не изменилось.
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        if enabled:
            # Запоминаем видимость панелей и скрываем их.
            self._map_fullscreen_restore = {
                "title_bar": self.title_bar.isVisible(),
                "left_rail": self.left_rail.isVisible(),
                "nav_toggle": self.nav_toggle_container.isVisible(),
                "nav_column": self.nav_column.isVisible(),
            }
            self._was_maximized_before_fullscreen = self.isMaximized()
            self.title_bar.setVisible(False)
            self.left_rail.setVisible(False)
            self.nav_toggle_container.setVisible(False)
            self.nav_column.setVisible(False)
            self.showFullScreen()
        else:
            # Возвращаем видимость панелей и режим окна.
            self.title_bar.setVisible(self._map_fullscreen_restore.get("title_bar", True))
            self.left_rail.setVisible(self._map_fullscreen_restore.get("left_rail", True))
            self.nav_toggle_container.setVisible(self._map_fullscreen_restore.get("nav_toggle", True))
            self.nav_column.setVisible(self._map_fullscreen_restore.get("nav_column", True))
            if self._was_maximized_before_fullscreen:
                self.showMaximized()
            else:
                self.showNormal()
            self.title_bar.sync_max_button()
        # Сообщаем рабочей области о смене полноэкранного режима.
        self.page_maps.set_map_fullscreen_state(enabled)
