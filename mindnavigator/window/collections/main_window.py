"""Главное окно приложения и связанная логика интерфейса.

Входные данные:
    События Qt, пользовательские действия и данные из рабочих областей.

Выходные данные:
    Отрисованные виджеты и изменения состояния интерфейса.
"""

from __future__ import annotations

import ctypes
import json
import sys
from datetime import datetime, timedelta
from typing import Mapping, cast
from PySide6.QtWidgets import (
    QDialog,
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
from PySide6.QtCore import Qt, QPoint, QRect, QEvent, QTimer, QByteArray
from pathlib import Path

from mindnavigator.spaceenity.constants import APP_NAME
from mindnavigator.hotkeys import HotkeyEventFilter, HotkeyManager, HotkeyOverridesStore, load_commands_from_json
from mindnavigator.spaceenity.i18n import DEFAULT_LANGUAGE, get_mode_labels, normalize_language_code
from mindnavigator.spaceenity.resources import resource_path
from mindnavigator.storage import DEFERRED_PRIORITY, get_database as _storage_get_database
from mindnavigator.ui.leftrail import LeftRail
from mindnavigator.ui.projects_nav import ProjectsNav
from mindnavigator.ui.search_nav import SearchNav
from mindnavigator.ui.command_palette import CommandPaletteDialog, PaletteCommand
from mindnavigator.ui.animations import DialogMinimizeAnimator
from mindnavigator.ui.dialogs.frameless_patch import restore_minimizable_task_dialog
from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog
from mindnavigator.ui.styles import TITLEBAR_BACKGROUND, build_app_stylesheet
from mindnavigator.ui.titlebar import TitleBar
from mindnavigator.services import GlobalSearchService
from mindnavigator.window.collections.windowing import ResizeEdge
from mindnavigator.workspaces.characters import CharactersWorkspace
from mindnavigator.workspaces.collections import CollectionsWorkspace
from mindnavigator.workspaces.dossier import DossierWorkspace
from mindnavigator.workspaces.files import FileWorkspace
from mindnavigator.workspaces.ideas import IdeasWorkspace
from mindnavigator.workspaces.maps import MapsListWorkspace
from mindnavigator.workspaces.minddraw import MindDrawWorkspace
from mindnavigator.workspaces.concept_board import ConceptBoardWorkspace
from mindnavigator.workspaces.notes import NoteWorkspace
from mindnavigator.workspaces.objects import ObjectWorkspace
from mindnavigator.workspaces.projects import ProjectsWorkspace
from mindnavigator.workspaces.purchases import PurchasesWorkspace
from mindnavigator.workspaces.settings import SettingsWorkspace
from mindnavigator.workspaces.tasks import TasksWorkspace


if sys.platform == "win32":
    class _WinMSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint),
            ("wParam", ctypes.c_size_t),
            ("lParam", ctypes.c_size_t),
            ("time", ctypes.c_uint),
            ("pt_x", ctypes.c_long),
            ("pt_y", ctypes.c_long),
        ]


def get_database():
    """Returns the shared database accessor for the main window."""
    return _storage_get_database()


def _qtimer_cls():
    """Returns the QTimer class used by delayed UI actions."""
    return QTimer


def normalize_enabled_workspace_ids(raw_value: str, available_ids: set[str]) -> set[str]:
    """Parses and normalizes enabled workspace ids from stored JSON value."""
    alias_map = {"mutaboard": "concept_board", "muta_board": "concept_board"}
    if not raw_value:
        return set(available_ids)
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return set(available_ids)
    if not isinstance(parsed, list):
        return set(available_ids)
    enabled = set()
    for item in parsed:
        normalized = str(item).strip()
        if not normalized:
            continue
        normalized = alias_map.get(normalized, normalized)
        if normalized in available_ids:
            enabled.add(normalized)
    return enabled if enabled else set(available_ids)


def normalize_nav_collapsed_setting(raw_value: str) -> bool:
    """Returns whether nav should be collapsed for persisted setting values."""
    normalized = str(raw_value).strip().lower()
    if normalized in {"0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return True


class MainWindow(QMainWindow):
    """Главное окно приложения с кастомным заголовком и рабочими областями."""

    RESIZE_MARGIN = 7
    SNAP_THRESHOLD = 14

    MODE_PROJECTS = "Проекты"
    MODE_TASKS = "Задачи"
    MODE_CONCEPTBOARD = "Концептборд"
    MODE_CONCEPTBOARD = MODE_CONCEPTBOARD
    MODE_PURCHASES = "Покупки"
    MODE_IDEAS = "Идеи"
    MODE_DOSSIER = "Досье"
    MODE_COLLECTIONS = "Коллекции"
    MODE_MAPS = "Карты"
    MODE_NOTES = "Заметки"
    MODE_FILES = "Файлы"
    MODE_OBJECTS = "Объекты"
    MODE_CHARACTERS = "Персонажи"
    MODE_MINDDRAW = "MindDraw"
    MODE_SETTINGS = "Настройки"
    APP_ENABLED_WORKSPACES_KEY = "app.enabled_workspaces"
    APP_LANGUAGE_KEY = "app.language"
    APP_THEME_KEY = "app.theme"
    APP_NAV_COLLAPSED_KEY = "app.nav_collapsed"
    _TRAY_RESTORE_HOTKEY_ID = 0x4D4E57
    _WM_HOTKEY = 0x0312
    _MOD_CONTROL = 0x0002
    _MOD_SHIFT = 0x0004

    def __init__(self):
        """Инициализирует окно, компоненты интерфейса и обработчики."""
        super().__init__()

        # Настраиваем базовые флаги окна и прозрачность.
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Включаем автозаливку, чтобы корректно рисовать фон.
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

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
        self._task_reminder_timer: QTimer | None = None
        self._task_remind_next_at: dict[int, datetime] = {}
        self._tray_message_task_id: int | None = None
        self._minimize_on_focus_lost = True
        self._focus_lost_tray_minimize_pending = False
        self._enabled_workspace_ids: set[str] = set()
        self._language_code = DEFAULT_LANGUAGE
        self._theme_mode = "dark"
        self._mode_labels = get_mode_labels(DEFAULT_LANGUAGE)
        self._current_mode = self.MODE_TASKS
        self._minimized_task_dialogs: dict[int, dict[str, object]] = {}
        self._minimized_task_dialog_animations: dict[int, object] = {}
        self._dialog_minimize_animator = DialogMinimizeAnimator()

        # Собираем интерфейс, связываем режимы и инициализируем трей.
        self._build_ui()
        self._wire_modes()
        self._init_tray()
        self._load_behavior_settings()
        self._init_task_reminders()
        self._init_hotkeys()
        self._register_system_restore_hotkey()

        # Включаем отслеживание мыши и фильтр событий для собственного ресайза.
        self.setMouseTracking(True)
        self.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            app.applicationStateChanged.connect(self._on_application_state_changed)

        # Выставляем стартовый режим.
        self.set_mode(self.MODE_TASKS)

    def _load_behavior_settings(self) -> None:
        db = get_database()
        value = db.get_setting("app.minimize_on_focus_lost", "1")
        self._minimize_on_focus_lost = value == "1"
        nav_collapsed_value = db.get_setting(self.APP_NAV_COLLAPSED_KEY, "1")
        self._set_nav_collapsed(normalize_nav_collapsed_setting(nav_collapsed_value), persist=False)
        theme_mode = db.get_setting(self.APP_THEME_KEY, "dark")
        self._apply_theme_mode(theme_mode, persist=False)
        language_code = db.get_setting(self.APP_LANGUAGE_KEY, DEFAULT_LANGUAGE)
        self._apply_ui_language(language_code)
        enabled_workspaces_raw = db.get_setting(self.APP_ENABLED_WORKSPACES_KEY, "")
        self._apply_workspace_visibility_from_raw(enabled_workspaces_raw)

    def _on_setting_changed(self, key: str, value: str) -> None:
        if key == "app.minimize_on_focus_lost":
            self._minimize_on_focus_lost = value == "1"
            return
        if key == self.APP_THEME_KEY:
            self._apply_theme_mode(value, persist=False)
            return
        if key == self.APP_LANGUAGE_KEY:
            normalized = normalize_language_code(value)
            if normalized == self._language_code:
                return
            self._apply_ui_language(normalized)
            answer = QMessageBox.question(
                self,
                "Смена языка",
                "Для полного применения нового языка требуется перезапуск. Перезапустить сейчас?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                QApplication.quit()
            return
        if key == self.APP_ENABLED_WORKSPACES_KEY:
            self._apply_workspace_visibility_from_raw(value)
            return

    def _workspace_mode_map(self) -> dict[str, str]:
        return {
            "projects": self.MODE_PROJECTS,
            "tasks": self.MODE_TASKS,
            "concept_board": self.MODE_CONCEPTBOARD,
            "purchases": self.MODE_PURCHASES,
            "ideas": self.MODE_IDEAS,
            "dossier": self.MODE_DOSSIER,
            "collections": self.MODE_COLLECTIONS,
            "maps": self.MODE_MAPS,
            "notes": self.MODE_NOTES,
            "files": self.MODE_FILES,
            "objects": self.MODE_OBJECTS,
            "characters": self.MODE_CHARACTERS,
            "minddraw": self.MODE_MINDDRAW,
        }

    def _enabled_workspace_ids_from_raw(self, raw_value: str) -> set[str]:
        all_workspace_ids = set(self._workspace_mode_map().keys())
        return normalize_enabled_workspace_ids(raw_value, all_workspace_ids)

    def _apply_workspace_visibility_from_raw(self, raw_value: str) -> None:
        self._apply_workspace_visibility(self._enabled_workspace_ids_from_raw(raw_value))

    def _apply_workspace_visibility(self, enabled_workspace_ids: set[str]) -> None:
        self._enabled_workspace_ids = set(enabled_workspace_ids)
        workspace_map = self._workspace_mode_map()
        for workspace_id, mode_name in workspace_map.items():
            button = self._mode_to_button.get(mode_name)
            if button is None:
                continue
            button.setVisible(workspace_id in self._enabled_workspace_ids)
        self.left_rail.refresh_hover_panel()
        if not self._is_mode_enabled(self._current_mode):
            self.set_mode(self._first_enabled_mode())

    def _is_mode_enabled(self, mode_name: str) -> bool:
        if mode_name == self.MODE_SETTINGS:
            return True
        mode_to_workspace_id = {mode: workspace_id for workspace_id, mode in self._workspace_mode_map().items()}
        workspace_id = mode_to_workspace_id.get(mode_name)
        if workspace_id is None:
            return True
        return workspace_id in self._enabled_workspace_ids

    def _first_enabled_mode(self) -> str:
        ordered_modes = [
            self.MODE_TASKS,
            self.MODE_CONCEPTBOARD,
            self.MODE_PROJECTS,
            self.MODE_PURCHASES,
            self.MODE_IDEAS,
            self.MODE_DOSSIER,
            self.MODE_COLLECTIONS,
            self.MODE_MAPS,
            self.MODE_NOTES,
            self.MODE_FILES,
            self.MODE_OBJECTS,
            self.MODE_CHARACTERS,
            self.MODE_MINDDRAW,
            self.MODE_SETTINGS,
        ]
        for mode_name in ordered_modes:
            if self._is_mode_enabled(mode_name):
                return mode_name
        return self.MODE_SETTINGS

    def _mode_caption(self, mode_name: str) -> str:
        return self._mode_labels.get(mode_name, mode_name)

    @staticmethod
    def _normalize_theme_mode(theme_mode: str) -> str:
        return "light" if str(theme_mode).strip().lower() == "light" else "dark"

    def _on_theme_toggled_from_rail(self, theme_mode: str) -> None:
        self._apply_theme_mode(theme_mode, persist=True)

    def _iter_theme_targets(self):
        target_names = (
            "search_nav",
            "projects_nav",
            "page_tasks",
            "page_concept_board",
            "page_projects",
            "page_purchases",
            "page_ideas",
            "page_dossier",
            "page_collections",
            "page_maps",
            "page_notes",
            "page_files",
            "page_objects",
            "page_characters",
            "page_minddraw",
            "page_settings",
        )
        for target_name in target_names:
            target = getattr(self, target_name, None)
            if target is not None:
                yield target

    def _apply_theme_mode(self, theme_mode: str, *, persist: bool) -> None:
        normalized = self._normalize_theme_mode(theme_mode)
        self._theme_mode = normalized
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_app_stylesheet(normalized))
        self.left_rail.set_theme_mode(normalized)
        for target in self._iter_theme_targets():
            set_theme_mode = getattr(target, "set_theme_mode", None)
            if callable(set_theme_mode):
                set_theme_mode(normalized)
        self._apply_titlebar_style()
        self._apply_root_style()
        if persist:
            get_database().set_setting(self.APP_THEME_KEY, normalized)

    def _apply_ui_language(self, language_code: str) -> None:
        self._language_code = normalize_language_code(language_code)
        self._mode_labels = get_mode_labels(self._language_code)
        self.left_rail.set_mode_labels(self._mode_labels)
        current_mode = getattr(self, "_current_mode", self.MODE_TASKS)
        mode_caption = self._mode_caption(current_mode)
        self.title_bar.title_label.setText(f"{APP_NAME} · {mode_caption}")
        self.projects_nav.set_mode_title(mode_caption)

    def minimize_task_dialog(self, dialog: QWidget, task_id: int, is_edit_dialog: bool) -> None:
        key = id(dialog)
        if key in self._minimized_task_dialogs:
            debug_task_dialog(f"main_window minimize skipped duplicate task_id={task_id} dialog={type(dialog).__name__}")
            return
        debug_task_dialog(
            f"main_window minimize start task_id={task_id} dialog={type(dialog).__name__} "
            f"is_edit={is_edit_dialog} visible={dialog.isVisible()}"
        )

        def _restore() -> None:
            self._restore_minimized_task_dialog(dialog)

        self._minimized_task_dialogs[key] = {
            "dialog": dialog,
            "task_id": int(task_id),
            "is_edit_dialog": bool(is_edit_dialog),
        }
        dialog.finished.connect(lambda _result, d=dialog: self._forget_minimized_task_dialog(d))
        self.title_bar.register_minimized_task_dialog(dialog, int(task_id), bool(is_edit_dialog), _restore)
        dialog.setEnabled(False)
        animation = self._dialog_minimize_animator.play(
            dialog,
            on_finished=lambda d=dialog: self._finalize_task_dialog_minimize_animation(d),
        )
        self._minimized_task_dialog_animations[key] = animation

    def _restore_minimized_task_dialog(self, dialog: QWidget) -> None:
        key = id(dialog)
        if key not in self._minimized_task_dialogs:
            return
        animation = self._minimized_task_dialog_animations.pop(key, None)
        if animation is not None:
            stop_fn = getattr(animation, "stop", None)
            if callable(stop_fn):
                stop_fn()
        self.title_bar.unregister_minimized_task_dialog(dialog)
        self._minimized_task_dialogs.pop(key, None)
        dialog.setEnabled(True)
        if isinstance(dialog, QDialog):
            restore_minimizable_task_dialog(dialog)
        else:
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()

    def _forget_minimized_task_dialog(self, dialog: QWidget) -> None:
        key = id(dialog)
        if key not in self._minimized_task_dialogs:
            return
        self._minimized_task_dialog_animations.pop(key, None)
        self.title_bar.unregister_minimized_task_dialog(dialog)
        self._minimized_task_dialogs.pop(key, None)

    def _finalize_task_dialog_minimize_animation(self, dialog: QWidget) -> None:
        key = id(dialog)
        self._minimized_task_dialog_animations.pop(key, None)
        if key not in self._minimized_task_dialogs:
            return
        dialog.hide()
        dialog.setEnabled(True)

    def _iter_visible_task_dialogs(self) -> list[QDialog]:
        app = QApplication.instance()
        if app is None:
            return []
        dialogs: list[QDialog] = []
        for widget in app.topLevelWidgets():
            if not isinstance(widget, QDialog):
                continue
            if not bool(widget.property("task_dialog_minimizable")):
                continue
            if not widget.isVisible():
                continue
            parent_window = widget.parentWidget().window() if widget.parentWidget() is not None else None
            if parent_window is not self:
                continue
            if self._dialog_has_visible_child_dialog(widget):
                continue
            dialogs.append(widget)
        dialogs.sort(key=lambda dialog: (dialog is QApplication.activeWindow(), dialog.isActiveWindow()))
        return dialogs

    @staticmethod
    def _widget_belongs_to_dialog(widget: QWidget, dialog: QDialog) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is dialog:
                return True
            current = current.parentWidget()
        return False

    @staticmethod
    def _dialog_has_visible_child_dialog(dialog: QDialog) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        active_modal = QApplication.activeModalWidget()
        if (
            isinstance(active_modal, QDialog)
            and active_modal is not dialog
            and active_modal.isVisible()
            and MainWindow._widget_belongs_to_dialog(active_modal, dialog)
        ):
            return True
        for widget in app.topLevelWidgets():
            if widget is dialog:
                continue
            if not isinstance(widget, QDialog):
                continue
            if not widget.isVisible():
                continue
            if MainWindow._widget_belongs_to_dialog(widget, dialog):
                return True
        return False

    def _maybe_minimize_task_dialog_from_app_click(self, global_pos: QPoint) -> bool:
        if QApplication.activePopupWidget() is not None:
            return False
        visible_dialogs = self._iter_visible_task_dialogs()
        if not visible_dialogs:
            return False
        debug_task_dialog(
            f"main_window app_click visible_dialogs={len(visible_dialogs)} global_pos=({global_pos.x()},{global_pos.y()})"
        )
        clicked_widget = QApplication.widgetAt(global_pos)
        target_dialog = visible_dialogs[-1]
        for dialog in reversed(visible_dialogs):
            if dialog.frameGeometry().contains(global_pos):
                return False
            if isinstance(clicked_widget, QWidget) and self._widget_belongs_to_dialog(clicked_widget, dialog):
                return False
            if dialog.isActiveWindow():
                target_dialog = dialog
                break
        task_id = int(target_dialog.property("task_dialog_id") or 0)
        if task_id <= 0:
            return False
        debug_task_dialog(
            f"main_window app_click minimize task_id={task_id} dialog={type(target_dialog).__name__} "
            f"clicked_widget={type(clicked_widget).__name__ if clicked_widget is not None else 'None'}"
        )
        self.minimize_task_dialog(
            target_dialog,
            task_id=task_id,
            is_edit_dialog=str(target_dialog.property("task_dialog_kind") or "").strip().lower() == "edit",
        )
        return True

    def _minimize_top_visible_task_dialog(self) -> bool:
        visible_dialogs = [
            dialog for dialog in self._iter_visible_task_dialogs() if not self._dialog_has_visible_child_dialog(dialog)
        ]
        if not visible_dialogs:
            return False
        target_dialog = visible_dialogs[-1]
        for dialog in reversed(visible_dialogs):
            if dialog.isActiveWindow():
                target_dialog = dialog
                break
        task_id = int(target_dialog.property("task_dialog_id") or 0)
        if task_id <= 0:
            return False
        self.minimize_task_dialog(
            target_dialog,
            task_id=task_id,
            is_edit_dialog=str(target_dialog.property("task_dialog_kind") or "").strip().lower() == "edit",
        )
        return True

    def _on_application_state_changed(self, state) -> None:
        if state == Qt.ApplicationState.ApplicationActive:
            return
        state_value = getattr(state, "value", state)
        debug_task_dialog(f"application_state_changed state={state_value}")
        self._minimize_top_visible_task_dialog()

    def _register_system_restore_hotkey(self) -> None:
        self._system_restore_hotkey_registered = False
        if sys.platform != "win32":
            return
        try:
            register_hotkey = getattr(ctypes.windll.user32, "RegisterHotKey", None)
            if not callable(register_hotkey):
                return
            hwnd = int(self.winId())
            result = register_hotkey(
                hwnd,
                self._TRAY_RESTORE_HOTKEY_ID,
                self._MOD_CONTROL | self._MOD_SHIFT,
                ord("W"),
            )
            self._system_restore_hotkey_registered = bool(result)
        except (AttributeError, OSError, TypeError, ValueError):
            self._system_restore_hotkey_registered = False

    def _unregister_system_restore_hotkey(self) -> None:
        if sys.platform != "win32":
            return
        if not getattr(self, "_system_restore_hotkey_registered", False):
            return
        try:
            unregister_hotkey = getattr(ctypes.windll.user32, "UnregisterHotKey", None)
            if callable(unregister_hotkey):
                unregister_hotkey(int(self.winId()), self._TRAY_RESTORE_HOTKEY_ID)
        finally:
            self._system_restore_hotkey_registered = False

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
        action_show.triggered.connect(self.restore_from_tray)
        action_quit.triggered.connect(QApplication.instance().quit)

        # Подключаем меню и обработчик кликов по иконке.
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.messageClicked.connect(self._on_tray_message_clicked)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Обрабатывает клики по иконке в трее."""
        # На одиночный клик восстанавливаем окно.
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            restore = getattr(self, "restore_from_tray", None)
            if callable(restore):
                restore()
            else:
                self._restore_from_tray()

    def _on_tray_message_clicked(self) -> None:
        task_id = self._tray_message_task_id
        self._tray_message_task_id = None
        restore = getattr(self, "restore_from_notification", None)
        if callable(restore):
            restore()
        else:
            self._restore_from_notification()
        if task_id is not None:
            self._open_task_from_tray_notification(task_id)

    def _open_task_from_tray_notification(self, task_id: int) -> None:
        self.set_mode(self.MODE_TASKS)
        if not hasattr(self.page_tasks, "focus_task"):
            return
        _qtimer_cls().singleShot(0, lambda target_task_id=task_id: self.page_tasks.focus_task(target_task_id))

    def _restore_from_tray(self):
        """Возвращает окно из трея."""
        # Восстанавливаем режим отображения до сворачивания.
        if self.isHidden():
            if self._was_maximized_before_minimize:
                self.showMaximized()
            else:
                self.showNormal()
                if not self._restore_geom.isNull():
                    self.setGeometry(self._restore_geom)
            self._was_maximized_before_minimize = False
        # Поднимаем окно поверх и синхронизируем состояние кнопки.
        self.raise_()
        self.activateWindow()
        self.title_bar.sync_max_button()

    def _restore_from_notification(self) -> None:
        """Разворачивает окно для перехода из системного уведомления."""
        if self.isHidden():
            self.showMaximized()
            self._was_maximized_before_minimize = False
        elif not self.isFullScreen() and not self.isMaximized():
            self.showMaximized()
        self.raise_()
        self.activateWindow()
        self.title_bar.sync_max_button()

    def restore_from_tray(self) -> None:
        self._restore_from_tray()

    def restore_from_notification(self) -> None:
        self._restore_from_notification()

    def _active_owned_dialog(self) -> QDialog | None:
        active_modal = QApplication.activeModalWidget()
        if isinstance(active_modal, QDialog):
            parent_window = active_modal.parentWidget().window() if active_modal.parentWidget() is not None else None
            if parent_window is self:
                return active_modal
        active_window = QApplication.activeWindow()
        if isinstance(active_window, QDialog):
            parent_window = active_window.parentWidget().window() if active_window.parentWidget() is not None else None
            if parent_window is self:
                return active_window
        return None

    def _should_minimize_to_tray_on_focus_lost(self) -> bool:
        if QApplication.applicationState() == Qt.ApplicationState.ApplicationActive:
            return False
        if not self._minimize_on_focus_lost or self._tray_icon is None:
            return False
        if not self.isVisible() or self.isHidden() or self.isMinimized():
            return False
        if self._active_owned_dialog() is not None:
            return False
        return True

    def _schedule_tray_minimize_on_focus_lost(self) -> None:
        if self._focus_lost_tray_minimize_pending:
            return
        self._focus_lost_tray_minimize_pending = True
        QTimer.singleShot(0, self._maybe_minimize_to_tray_on_focus_lost)

    def _maybe_minimize_to_tray_on_focus_lost(self) -> None:
        self._focus_lost_tray_minimize_pending = False
        if not self._should_minimize_to_tray_on_focus_lost():
            return
        self._minimize_to_tray()

    def _minimize_to_tray(self):
        """Сворачивает окно в трей."""
        # Если трей не создан, выходим без действий.
        if self._tray_icon is None:
            return
        self._focus_lost_tray_minimize_pending = False
        self._was_maximized_before_minimize = self._was_maximized_before_minimize or self.isMaximized()
        if not self._was_maximized_before_minimize:
            geom = self.normalGeometry() if self.isMinimized() else self.geometry()
            if not geom.isNull() and geom.width() > 0 and geom.height() > 0:
                self._restore_geom = QRect(geom)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        # Прячем окно и показываем уведомление.
        self.hide()
        self._tray_message_task_id = None
        self._tray_icon.showMessage(
            APP_NAME,
            "Приложение свернуто в трей.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def minimize_to_tray(self) -> None:
        """Сворачивает окно: в трей при наличии, иначе стандартно в панель задач."""
        if self._tray_icon is not None:
            self._minimize_to_tray()
            return
        self.showMinimized()

    @staticmethod
    def _hotkey_defaults_path() -> Path:
        return Path(__file__).resolve().parents[3] / "defaults" / "hotkeys.default.json"

    def _init_task_reminders(self) -> None:
        """Запускает периодические напоминания о просроченных задачах."""
        timer_cls = _qtimer_cls()
        self._task_reminder_timer = timer_cls(self)
        self._task_reminder_timer.setInterval(60 * 1000)
        self._task_reminder_timer.timeout.connect(self._check_task_reminders)
        self._task_reminder_timer.start()
        timer_cls.singleShot(10 * 1000, self._check_task_reminders)

    def _check_task_reminders(self) -> None:
        """Показывает напоминания каждые 30 минут до переноса или выполнения задачи."""
        if self._tray_icon is None:
            return
        now = datetime.now()
        due_tasks = []
        active_due_ids: set[int] = set()
        for task in get_database().fetch_tasks():
            if task.done or task.priority == DEFERRED_PRIORITY:
                continue
            planned = datetime.combine(task.day, datetime.min.time())
            time_text = (task.time_text or "").strip()
            if time_text:
                try:
                    planned = datetime.strptime(
                        f"{task.day.isoformat()} {time_text}",
                        "%Y-%m-%d %H:%M",
                    )
                except ValueError:
                    planned = datetime.combine(task.day, datetime.min.time())
            if planned > now:
                continue
            active_due_ids.add(task.id)
            due_tasks.append((planned, task))

        stale_ids = [task_id for task_id in self._task_remind_next_at if task_id not in active_due_ids]
        for task_id in stale_ids:
            self._task_remind_next_at.pop(task_id, None)

        due_tasks.sort(key=lambda item: (item[0], item[1].id))
        for planned, task in due_tasks:
            next_at = self._task_remind_next_at.get(task.id)
            if next_at is not None and now < next_at:
                continue
            due_text = planned.strftime("%Y-%m-%d %H:%M")
            self._tray_message_task_id = task.id
            self._tray_icon.showMessage(
                APP_NAME,
                f"Напоминание о задаче: {task.title}\nСрок: {due_text}",
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
            self._task_remind_next_at[task.id] = now + timedelta(minutes=30)

    @staticmethod
    def _hotkey_overrides_path() -> Path:
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
            self.MODE_PURCHASES: "Purchases",
            self.MODE_IDEAS: "Ideas",
            self.MODE_DOSSIER: "Dossier",
            self.MODE_COLLECTIONS: "Collections",
            self.MODE_MAPS: "Maps",
            self.MODE_NOTES: "Notes",
            self.MODE_FILES: "Files",
            self.MODE_OBJECTS: "Objects",
            self.MODE_CHARACTERS: "Characters",
            self.MODE_CONCEPTBOARD: "ConceptBoard",
            self.MODE_MINDDRAW: "MindDraw",
            self.MODE_SETTINGS: "Settings",
        }
        return mapping.get(self._current_mode, "Tasks")

    def _cycle_workspace(self, direction: int) -> None:
        modes = [mode_name for mode_name in self._page_index.keys() if self._is_mode_enabled(mode_name)]
        if not modes:
            return
        if self._current_mode not in modes:
            self.set_mode(self._first_enabled_mode())
            return
        current_idx = modes.index(self._current_mode)
        next_idx = (current_idx + direction) % len(modes)
        self.set_mode(modes[next_idx])

    def _cycle_entity_sheet(self, direction: int) -> None:
        workspace = self.workspace_stack.currentWidget()
        if workspace is None:
            return
        if direction > 0:
            show_next = getattr(workspace, "show_next", None) or getattr(workspace, "_show_next", None)
            if callable(show_next):
                show_next()
        elif direction < 0:
            show_previous = getattr(workspace, "show_previous", None) or getattr(workspace, "_show_previous", None)
            if callable(show_previous):
                show_previous()

    def _hotkey_create_task(self) -> None:
        self.set_mode(self.MODE_TASKS)
        if hasattr(self.page_tasks, "open_create_task_dialog"):
            self.page_tasks.open_create_task_dialog()
            return
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
        commands = [
            PaletteCommand(command, binding)
            for command, binding in self.hotkeys.get_active_hotkeys()
            if command.id != "ui.command_palette" and command.id in self._hotkey_callbacks
        ]
        dialog = CommandPaletteDialog(
            search_service=GlobalSearchService(get_database()),
            commands=commands,
            theme_mode=self._theme_mode,
            parent=self,
        )
        dialog.itemActivated.connect(self._activate_command_palette_item)
        dialog.exec()

    def _activate_command_palette_item(self, item_kind: str, payload: object) -> None:
        if item_kind == "entity" and isinstance(payload, dict):
            self._on_search_result_activated(payload)
            return
        if item_kind == "command" and isinstance(payload, str):
            callback = self._resolve_hotkey_callback(payload)
            if callable(callback):
                callback()

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
        self.left_rail.set_expand_host(body)
        self.left_rail.theme_toggled.connect(self._on_theme_toggled_from_rail)
        self.left_rail.hotkeys_help_requested.connect(self._show_hotkeys_help)

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
        self.nav_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.page_concept_board = ConceptBoardWorkspace()
        self.page_projects = ProjectsWorkspace()
        self.page_purchases = PurchasesWorkspace()
        self.page_ideas = IdeasWorkspace()
        self.page_dossier = DossierWorkspace()
        self.page_collections = CollectionsWorkspace()
        self.page_maps = MapsListWorkspace()
        self.page_notes = NoteWorkspace()
        self.page_files = FileWorkspace()
        self.page_objects = ObjectWorkspace()
        self.page_characters = CharactersWorkspace()
        self.page_minddraw = MindDrawWorkspace()
        self.page_settings = SettingsWorkspace()
        self.page_settings.setting_changed.connect(self._on_setting_changed)

        # Регистрируем страницы и сохраняем их индексы.
        self._page_index = {
            self.MODE_PROJECTS: self.workspace_stack.addWidget(self.page_projects),
            self.MODE_TASKS: self.workspace_stack.addWidget(self.page_tasks),
            self.MODE_CONCEPTBOARD: self.workspace_stack.addWidget(self.page_concept_board),
            self.MODE_PURCHASES: self.workspace_stack.addWidget(self.page_purchases),
            self.MODE_IDEAS: self.workspace_stack.addWidget(self.page_ideas),
            self.MODE_DOSSIER: self.workspace_stack.addWidget(self.page_dossier),
            self.MODE_COLLECTIONS: self.workspace_stack.addWidget(self.page_collections),
            self.MODE_MAPS: self.workspace_stack.addWidget(self.page_maps),
            self.MODE_NOTES: self.workspace_stack.addWidget(self.page_notes),
            self.MODE_FILES: self.workspace_stack.addWidget(self.page_files),
            self.MODE_OBJECTS: self.workspace_stack.addWidget(self.page_objects),
            self.MODE_CHARACTERS: self.workspace_stack.addWidget(self.page_characters),
            self.MODE_MINDDRAW: self.workspace_stack.addWidget(self.page_minddraw),
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
        self._set_nav_collapsed(True, persist=False)

    @staticmethod
    def _placeholder(title: str, subtitle: str) -> QWidget:
        """Возвращает временный экран-заглушку для неготовых режимов."""
        # Заглушка для режимов без реализации.
        w = QWidget()
        w.setObjectName("Placeholder")
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet("color:#cfcfcf; font-size:22px;")
        s = QLabel(subtitle)
        s.setStyleSheet("color:#7a7a7a; font-size:13px;")
        s.setWordWrap(True)
        s.setMaximumWidth(640)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t)
        l.addWidget(s)
        w.setStyleSheet("QWidget#Placeholder { background: #16171a; }")
        return w

    def _apply_titlebar_style(self) -> None:
        """Применяет стили к заголовку окна."""
        is_light = self._theme_mode == "light"
        title_background = (
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            " stop:0 #f1f4ff, stop:0.5 #e9edf8, stop:0.5001 #e4e8f1, stop:1 #e4e8f1);"
            if is_light
            else TITLEBAR_BACKGROUND
        )
        border_color = "#cfd4de" if is_light else "#2a2b2f"
        title_color = "#1d2435" if is_light else "#eef1ff"
        button_color = "#374056" if is_light else "#cfcfcf"
        hover_bg = "#dbe3f5" if is_light else "#2a2b2f"
        pressed_bg = "#cbd7f0" if is_light else "#35363c"
        chip_text = "#27324b" if is_light else "#d8dbe7"
        chip_bg = "#d9e2f6" if is_light else "#2a2d36"
        chip_border = "#b8c5e1" if is_light else "#3a3f4b"
        chip_hover = "#c9d6f1" if is_light else "#343a49"
        arrow_text = "#2f3b57" if is_light else "#cfcfcf"
        arrow_bg = "#d7e0f2" if is_light else "#262a34"
        arrow_border = "#b7c3de" if is_light else "#3a3f4b"
        arrow_hover = "#c4d2ef" if is_light else "#303647"
        # Устанавливаем стили для заголовка и кнопок управления.
        self.title_bar.setStyleSheet(f"""
            QWidget#TitleBar {{
                {title_background}
                border-bottom: 1px solid {border_color};
            }}
            QLabel#TitleText {{
                color: {title_color};
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
            QToolButton {{
                color: {button_color};
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QToolButton:hover {{ background: {hover_bg}; }}
            QToolButton:pressed {{ background: {pressed_bg}; }}
            QToolButton:last-child:hover {{
                background: #b23b3b;
                color: #ffffff;
            }}
            QToolButton#MinimizedTaskChip {{
                color: {chip_text};
                background: {chip_bg};
                border: 1px solid {chip_border};
                border-radius: 7px;
                padding: 2px 8px;
                min-height: 22px;
            }}
            QToolButton#MinimizedTaskChip:hover {{
                background: {chip_hover};
            }}
            QToolButton#MinimizedDialogsArrow {{
                color: {arrow_text};
                background: {arrow_bg};
                border: 1px solid {arrow_border};
                border-radius: 6px;
                font-size: 10px;
                padding: 0;
            }}
            QToolButton#MinimizedDialogsArrow:hover {{
                background: {arrow_hover};
            }}
        """)

    def _apply_root_style(self) -> None:
        """Применяет базовые стили к корневому контейнеру."""
        is_light = self._theme_mode == "light"
        outer_background = (
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #eef2fb, stop:0.5 #e8edf8, stop:0.6001 #e7ecf7, stop:1 #e7ecf7);"
            if is_light
            else "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #1c181b, stop:0.5 #101217, stop:0.6001 #101217, stop:1 #101217);"
        )
        container_border = "#cad0dc" if is_light else "#2a2b2f"
        nav_toggle_bg = "#edf1f9" if is_light else "#1e1f22"
        nav_toggle_border = "#cfd4de" if is_light else "#2a2b2f"
        nav_button_color = "#344056" if is_light else "#cfcfcf"
        nav_button_hover = "#dbe3f5" if is_light else "#2a2b2f"
        # Прописываем стили для фона, контейнера и кнопки навигации.
        self.centralWidget().setStyleSheet(f"""
            QWidget#OuterRoot {{
                {outer_background}
                background-position: top left;
                background-repeat: repeat;
            }}
            QWidget#Container {{ border: 1px solid {container_border}; }}
            QWidget#NavToggleContainer {{
                background: {nav_toggle_bg};
                border-right: 1px solid {nav_toggle_border};
            }}
            QToolButton#NavToggleButton {{
                background: transparent;
                border: none;
                color: {nav_button_color};
                font-size: 16px;
                padding: 4px 2px;
            }}
            QToolButton#NavToggleButton:hover {{
                background: {nav_button_hover};
            }}
        """)

    def _apply_nav_state_to_workspace(self, workspace: QWidget) -> None:
        # Передаем активное состояние навигации в рабочие области.
        if hasattr(workspace, "set_nav_collapsed_state"):
            workspace.set_nav_collapsed_state(not self.nav_column.isVisible())

    def _set_nav_collapsed(self, collapsed: bool, *, persist: bool = True) -> None:
        # Скрываем/показываем колонку навигации и меняем подсказки.
        self.nav_column.setVisible(not collapsed)
        self.nav_toggle.setText("⟩" if collapsed else "⟨")
        self.nav_toggle.setToolTip("Развернуть навигацию" if collapsed else "Свернуть навигацию")
        if persist:
            get_database().set_setting(self.APP_NAV_COLLAPSED_KEY, "1" if collapsed else "0")
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
            self.left_rail.btn_concept_board: self.MODE_CONCEPTBOARD,
            self.left_rail.btn_purchases: self.MODE_PURCHASES,
            self.left_rail.btn_ideas: self.MODE_IDEAS,
            self.left_rail.btn_dossier: self.MODE_DOSSIER,
            self.left_rail.btn_collections: self.MODE_COLLECTIONS,
            self.left_rail.btn_maps: self.MODE_MAPS,
            self.left_rail.btn_notes: self.MODE_NOTES,
            self.left_rail.btn_files: self.MODE_FILES,
            self.left_rail.btn_objects: self.MODE_OBJECTS,
            self.left_rail.btn_characters: self.MODE_CHARACTERS,
            self.left_rail.btn_minddraw: self.MODE_MINDDRAW,
            self.left_rail.btn_settings: self.MODE_SETTINGS,
        }
        self._mode_to_button = {mode_name: button for button, mode_name in self._btn_to_mode.items()}
        # Подключаем клики на кнопки к смене режима.
        for btn, mode in self._btn_to_mode.items():
            btn.clicked.connect(lambda checked=False, m=mode: self.set_mode(m))

    def set_mode(self, mode_name: str):
        """Переключает активную рабочую область и обновляет заголовки."""
        if not self._is_mode_enabled(mode_name):
            mode_name = self._first_enabled_mode()
        mode_caption = self._mode_caption(mode_name)
        # Обновляем заголовок окна и состояние навигации.
        self.title_bar.title_label.setText(f"{APP_NAME} · {mode_caption}")
        previous_workspace = self.workspace_stack.currentWidget()
        if previous_workspace is not None and hasattr(previous_workspace, "on_leave"):
            previous_workspace.on_leave()
        self._current_mode = mode_name
        self.projects_nav.set_mode_title(mode_caption)
        # Переключаем страницу в стеке.
        self.workspace_stack.setCurrentIndex(self._page_index.get(mode_name, self._page_index[self.MODE_TASKS]))
        self._apply_nav_state_to_workspace(self.workspace_stack.currentWidget())
        current_workspace = self.workspace_stack.currentWidget()
        if current_workspace is not None and hasattr(current_workspace, "on_enter"):
            current_workspace.on_enter(None)
        # Обновляем данные активной страницы.
        if mode_name == self.MODE_TASKS:
            self.page_tasks.refresh_tasks()
        elif mode_name == self.MODE_CONCEPTBOARD:
            self.page_concept_board.refresh()
        elif mode_name == self.MODE_PURCHASES:
            if hasattr(self.page_purchases, "refresh"):
                self.page_purchases.refresh()
        elif mode_name == self.MODE_IDEAS:
            self.page_ideas.refresh()
            if hasattr(self.page_ideas, "refresh_current_relations"):
                self.page_ideas.refresh_current_relations()
        elif mode_name == self.MODE_DOSSIER:
            self.page_dossier.refresh()
        elif mode_name == self.MODE_COLLECTIONS:
            self.page_collections.refresh_collections()
        elif mode_name == self.MODE_PROJECTS:
            self.page_projects.refresh_projects()
        elif mode_name == self.MODE_OBJECTS:
            self.page_objects.refresh_objects()
        elif mode_name == self.MODE_CHARACTERS:
            self.page_characters.refresh_characters()

        # Отмечаем выбранную кнопку в меню.
        for btn, m in self._btn_to_mode.items():
            if m == mode_name:
                btn.setChecked(True)
                break

        self._update_hotkey_contexts()

    def _on_nav_filter_changed(self, kind: str, value: object) -> None:
        # Определяем активный режим и прокидываем фильтры в соответствующий вид.
        payload = cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}
        entity_id = payload.get("id")
        project_title = payload.get("title")
        map_project = payload.get("project")

        mode = self._current_mode
        if mode == self.MODE_TASKS:
            if kind == "project" and isinstance(entity_id, int):
                self.page_tasks.set_project_filter(entity_id)
            elif kind == "clear":
                self.page_tasks.set_project_filter(None)
            return
        if mode == self.MODE_PROJECTS:
            if kind == "task" and isinstance(entity_id, int):
                self.page_projects.set_task_filter(entity_id)
            elif kind == "clear":
                self.page_projects.set_task_filter(None)
            return
        if mode == self.MODE_FILES:
            if kind == "project" and isinstance(entity_id, int):
                self.page_files.set_project_filter(entity_id)
            elif kind == "clear":
                self.page_files.set_project_filter(None)
            return
        if mode == self.MODE_MAPS:
            if kind == "project" and isinstance(project_title, str):
                self.page_maps.set_project_filter(project_title)
            elif kind == "clear":
                self.page_maps.set_project_filter(None)
            return
        if mode == self.MODE_NOTES:
            if kind == "task" and isinstance(entity_id, int):
                self.page_notes.set_task_filter(entity_id)
            elif kind == "map":
                project = map_project if isinstance(map_project, str) and map_project else None
                self.page_notes.set_project_filter(project)
            elif kind == "clear":
                self.page_notes.set_project_filter(None)
                self.page_notes.set_task_filter(None)
            return
        if mode == self.MODE_OBJECTS:
            if kind == "project" and isinstance(entity_id, int):
                self.page_objects.set_project_filter(entity_id)
            elif kind == "task" and isinstance(entity_id, int):
                self.page_objects.set_task_filter(entity_id)
            elif kind == "marker" and isinstance(entity_id, int):
                self.page_objects.set_marker_filter(entity_id)
            elif kind == "clear":
                self.page_objects.set_project_filter(None)
                self.page_objects.set_task_filter(None)
                self.page_objects.set_marker_filter(None)
            return
        if mode == self.MODE_CHARACTERS:
            if kind in {"project", "task", "map", "marker"} and isinstance(entity_id, int):
                self.page_characters.set_entity_filter(kind, entity_id)
            elif kind == "clear":
                self.page_characters.set_entity_filter(None, None)
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
        elif entity == "idea":
            self.set_mode(self.MODE_IDEAS)
            idea_id = payload.get("id")
            if idea_id is not None and hasattr(self.page_ideas, "select_idea"):
                self.page_ideas.select_idea(int(idea_id))
        elif entity == "file":
            self.set_mode(self.MODE_FILES)
        elif entity == "object":
            self.set_mode(self.MODE_OBJECTS)
        elif entity == "collection":
            self.set_mode(self.MODE_COLLECTIONS)
            item_id = payload.get("id")
            if item_id is not None and hasattr(self.page_collections, "focus_item"):
                self.page_collections.focus_item(int(item_id))
        elif entity == "character":
            self.set_mode(self.MODE_CHARACTERS)
            character_id = payload.get("id")
            if character_id is not None and hasattr(self.page_characters, "focus_character"):
                self.page_characters.focus_character(int(character_id))

    def resizeEvent(self, event):
        """Обрабатывает ресайз окна, синхронизируя ширину навигации."""
        # Передаем событие базовому классу и обновляем ширину панелей.
        super().resizeEvent(event)
        if not self.isMaximized() and not self.isMinimized() and self.isVisible():
            self._restore_geom = self.geometry()
        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self.isMaximized() and not self.isMinimized() and self.isVisible():
            self._restore_geom = self.geometry()

    def closeEvent(self, event):
        if self.title_bar.has_minimized_task_edit_dialogs():
            QMessageBox.warning(
                self,
                "Незавершённые окна",
                "Нельзя закрыть приложение: есть свёрнутые окна редактирования задач. "
                "Восстановите или закройте их перед выходом.",
            )
            event.ignore()
            return
        self._unregister_system_restore_hotkey()
        if hasattr(self, "hotkey_store") and hasattr(self, "hotkeys"):
            try:
                self.hotkey_store.save(self.hotkeys)
            except OSError:
                # Ignore write failures on read-only profiles; app shutdown must continue.
                pass
        super().closeEvent(event)

    def nativeEvent(self, event_type, message):
        if isinstance(event_type, (bytes, bytearray, memoryview)):
            event_name = bytes(event_type).decode("utf-8", errors="ignore")
        elif isinstance(event_type, QByteArray):
            event_name = bytes(event_type.data()).decode("utf-8", errors="ignore")
        else:
            event_name = str(event_type)
        if (
            sys.platform == "win32"
            and getattr(self, "_system_restore_hotkey_registered", False)
            and event_name in {"windows_generic_MSG", "windows_dispatcher_MSG"}
        ):
            raw_message: int | None
            if isinstance(message, int):
                raw_message = message
            else:
                try:
                    raw_message = int(message)
                except (TypeError, ValueError):
                    raw_message = None
            if not raw_message:
                return super().nativeEvent(event_type, message)
            try:
                msg_ptr = ctypes.c_void_p(raw_message)
                msg = ctypes.cast(msg_ptr, ctypes.POINTER(_WinMSG)).contents
            except (TypeError, ValueError, ctypes.ArgumentError):
                return super().nativeEvent(event_type, message)
            if msg.message == self._WM_HOTKEY and int(msg.wParam) == self._TRAY_RESTORE_HOTKEY_ID:
                self._restore_from_tray()
                return True, 0
        return super().nativeEvent(event_type, message)

    def changeEvent(self, event):
        """Обрабатывает сворачивание окна для отправки в трей."""
        # Отслеживаем сворачивание и отправляем окно в трей.
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            old_state = event.oldState() if hasattr(event, "oldState") else Qt.WindowState.WindowNoState
            self._was_maximized_before_minimize = bool(old_state & Qt.WindowState.WindowMaximized)
            self._minimize_to_tray()
            return
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self._schedule_tray_minimize_on_focus_lost()

    def keyPressEvent(self, event):
        """Обрабатывает горячие клавиши окна."""
        # Esc закрывает полноэкранный режим карты.
        if event.key() == Qt.Key.Key_Escape and self._map_fullscreen_active:
            self.set_map_fullscreen(False)
            event.accept()
            return
        # F11 переключает полноэкранный режим окна.
        if event.key() == Qt.Key.Key_F11:
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

    def snap_to_screen_edges(self, global_pos: QPoint) -> None:
        self._snap_to_screen_edges(global_pos)

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

    @staticmethod
    def _cursor_for_edge(edge: ResizeEdge):
        """Return cursor shape for selected resize edge."""
        # Select cursor icon for current resize edge orientation.
        edge_value = int(edge.value)
        left = int(ResizeEdge.LEFT.value)
        right = int(ResizeEdge.RIGHT.value)
        top = int(ResizeEdge.TOP.value)
        bottom = int(ResizeEdge.BOTTOM.value)
        diagonal_forward = {
            top | left,
            bottom | right,
        }
        diagonal_backward = {
            top | right,
            bottom | left,
        }
        if edge_value in (left, right):
            return Qt.CursorShape.SizeHorCursor
        if edge_value in (top, bottom):
            return Qt.CursorShape.SizeVerCursor
        if edge_value in diagonal_forward:
            return Qt.CursorShape.SizeFDiagCursor
        if edge_value in diagonal_backward:
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

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
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and hasattr(event, "button")
            and hasattr(event, "globalPosition")
            and event.button() == Qt.MouseButton.LeftButton
        ):
            global_pos = event.globalPosition().toPoint()
            if self._maybe_minimize_task_dialog_from_app_click(global_pos):
                return False
        # Обрабатываем события только для самого окна.
        if obj is self:
            # 🔥 В maximized полностью выключаем hit-test и дергание курсора
            if self.isMaximized():
                if event.type() in (QEvent.Type.MouseMove, QEvent.Type.Leave):
                    self.unsetCursor()
                return super().eventFilter(obj, event)

            if event.type() == QEvent.Type.MouseMove and hasattr(event, "position") and hasattr(event, "globalPosition"):
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

            if event.type() == QEvent.Type.MouseButtonPress and hasattr(event, "button") and hasattr(event, "position"):
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = event.position().toPoint()
                    edge = self._hit_test_edges(pos)
                    if edge != ResizeEdge.NONE:
                        # Запускаем ресайз при нажатии на край.
                        if hasattr(event, "globalPosition"):
                            self._start_resize(edge, event.globalPosition().toPoint())
                        return True
                return False

            if event.type() == QEvent.Type.MouseButtonRelease:
                # Останавливаем ресайз по отпусканию.
                if self._resizing:
                    self._stop_resize()
                    return True
                return False

            if event.type() == QEvent.Type.Leave:
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

