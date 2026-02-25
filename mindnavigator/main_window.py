"""Р“Р»Р°РІРЅРѕРµ РѕРєРЅРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ Рё СЃРІСЏР·Р°РЅРЅР°СЏ Р»РѕРіРёРєР° РёРЅС‚РµСЂС„РµР№СЃР°.

Р’С…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ:
    РЎРѕР±С‹С‚РёСЏ Qt, РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ РґРµР№СЃС‚РІРёСЏ Рё РґР°РЅРЅС‹Рµ РёР· СЂР°Р±РѕС‡РёС… РѕР±Р»Р°СЃС‚РµР№.

Р’С‹С…РѕРґРЅС‹Рµ РґР°РЅРЅС‹Рµ:
    РћС‚СЂРёСЃРѕРІР°РЅРЅС‹Рµ РІРёРґР¶РµС‚С‹ Рё РёР·РјРµРЅРµРЅРёСЏ СЃРѕСЃС‚РѕСЏРЅРёСЏ РёРЅС‚РµСЂС„РµР№СЃР°.
"""

from __future__ import annotations

import ctypes
import json
import sys
from datetime import datetime, timedelta
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
from PySide6.QtCore import Qt, QPoint, QRect, QEvent, QTimer
from pathlib import Path

from .windowing import ResizeEdge
from .ui.titlebar import TitleBar
from .ui.leftrail import LeftRail
from .ui.projects_nav import ProjectsNav
from .ui.search_nav import SearchNav
from .workspaces.tasks_workspace import TasksWorkspace
from .workspaces.projects_workspace import ProjectsWorkspace
from .workspaces.collections_workspace import CollectionsWorkspace
from .workspaces.maps_workspace import MapsListWorkspace
from .workspaces.notes_workspace import NoteWorkspace
from .workspaces.settings_workspace import SettingsWorkspace
from .workspaces.files_workspace import FileWorkspace
from .workspaces.objects_workspace import ObjectWorkspace
from .workspaces.ideas_workspace import IdeasWorkspace
from .workspaces.purchases_workspace import PurchasesWorkspace
from .constants import APP_NAME
from .i18n import DEFAULT_LANGUAGE, get_mode_labels, normalize_language_code
from .resources import resource_path
from .hotkeys import HotkeyEventFilter, HotkeyManager, HotkeyOverridesStore, load_commands_from_json
from .storage import get_database

from .ui.styles import TITLEBAR_BACKGROUND


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


def normalize_enabled_workspace_ids(raw_value: str, available_ids: set[str]) -> set[str]:
    """Parses and normalizes enabled workspace ids from stored JSON value."""
    if not raw_value:
        return set(available_ids)
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return set(available_ids)
    if not isinstance(parsed, list):
        return set(available_ids)
    enabled = {str(item).strip() for item in parsed if str(item).strip() in available_ids}
    return enabled if enabled else set(available_ids)


class MainWindow(QMainWindow):
    """Р“Р»Р°РІРЅРѕРµ РѕРєРЅРѕ РїСЂРёР»РѕР¶РµРЅРёСЏ СЃ РєР°СЃС‚РѕРјРЅС‹Рј Р·Р°РіРѕР»РѕРІРєРѕРј Рё СЂР°Р±РѕС‡РёРјРё РѕР±Р»Р°СЃС‚СЏРјРё."""

    RESIZE_MARGIN = 7
    SNAP_THRESHOLD = 14

    MODE_PROJECTS = "РџСЂРѕРµРєС‚С‹"
    MODE_TASKS = "Р—Р°РґР°С‡Рё"
    MODE_PURCHASES = "РџРѕРєСѓРїРєРё"
    MODE_IDEAS = "РРґРµРё"
    MODE_COLLECTIONS = "РљРѕР»Р»РµРєС†РёРё"
    MODE_MAPS = "РљР°СЂС‚С‹"
    MODE_NOTES = "Р—Р°РјРµС‚РєРё"
    MODE_FILES = "Р¤Р°Р№Р»С‹"
    MODE_OBJECTS = "РћР±СЉРµРєС‚С‹"
    MODE_SETTINGS = "РќР°СЃС‚СЂРѕР№РєРё"
    APP_ENABLED_WORKSPACES_KEY = "app.enabled_workspaces"
    APP_LANGUAGE_KEY = "app.language"
    _TRAY_RESTORE_HOTKEY_ID = 0x4D4E57
    _WM_HOTKEY = 0x0312
    _MOD_CONTROL = 0x0002
    _MOD_SHIFT = 0x0004

    def __init__(self):
        """РРЅРёС†РёР°Р»РёР·РёСЂСѓРµС‚ РѕРєРЅРѕ, РєРѕРјРїРѕРЅРµРЅС‚С‹ РёРЅС‚РµСЂС„РµР№СЃР° Рё РѕР±СЂР°Р±РѕС‚С‡РёРєРё."""
        super().__init__()

        # РќР°СЃС‚СЂР°РёРІР°РµРј Р±Р°Р·РѕРІС‹Рµ С„Р»Р°РіРё РѕРєРЅР° Рё РїСЂРѕР·СЂР°С‡РЅРѕСЃС‚СЊ.
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Р’РєР»СЋС‡Р°РµРј Р°РІС‚РѕР·Р°Р»РёРІРєСѓ, С‡С‚РѕР±С‹ РєРѕСЂСЂРµРєС‚РЅРѕ СЂРёСЃРѕРІР°С‚СЊ С„РѕРЅ.
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # РћРїСЂРµРґРµР»СЏРµРј РјРёРЅРёРјР°Р»СЊРЅС‹Рµ СЂР°Р·РјРµСЂС‹ Рё РёРєРѕРЅРєСѓ РїСЂРёР»РѕР¶РµРЅРёСЏ.
        self.setMinimumSize(1100, 700)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        # РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј СЃРѕСЃС‚РѕСЏРЅРёРµ РєР°СЃС‚РѕРјРЅРѕРіРѕ СЂРµСЃР°Р№Р·Р°.
        self._resize_edge = ResizeEdge.NONE
        self._resizing = False
        self._press_global = QPoint()
        self._start_geom = QRect()

        # РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј СЃРѕСЃС‚РѕСЏРЅРёРµ С‚СЂРµСЏ, РїРѕР»РЅРѕСЌРєСЂР°РЅРЅРѕРіРѕ СЂРµР¶РёРјР° РєР°СЂС‚С‹ Рё РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РіРµРѕРјРµС‚СЂРёРё.
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
        self._enabled_workspace_ids: set[str] = set()
        self._language_code = DEFAULT_LANGUAGE
        self._mode_labels = get_mode_labels(DEFAULT_LANGUAGE)
        self._current_mode = self.MODE_TASKS

        # РЎРѕР±РёСЂР°РµРј РёРЅС‚РµСЂС„РµР№СЃ, СЃРІСЏР·С‹РІР°РµРј СЂРµР¶РёРјС‹ Рё РёРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј С‚СЂРµР№.
        self._build_ui()
        self._wire_modes()
        self._init_tray()
        self._load_behavior_settings()
        self._init_task_reminders()
        self._init_hotkeys()
        self._register_system_restore_hotkey()

        # Р’РєР»СЋС‡Р°РµРј РѕС‚СЃР»РµР¶РёРІР°РЅРёРµ РјС‹С€Рё Рё С„РёР»СЊС‚СЂ СЃРѕР±С‹С‚РёР№ РґР»СЏ СЃРѕР±СЃС‚РІРµРЅРЅРѕРіРѕ СЂРµСЃР°Р№Р·Р°.
        self.setMouseTracking(True)
        self.installEventFilter(self)

        # Р’С‹СЃС‚Р°РІР»СЏРµРј СЃС‚Р°СЂС‚РѕРІС‹Р№ СЂРµР¶РёРј.
        self.set_mode(self.MODE_TASKS)

    def _load_behavior_settings(self) -> None:
        db = get_database()
        value = db.get_setting("app.minimize_on_focus_lost", "1")
        self._minimize_on_focus_lost = value == "1"
        language_code = db.get_setting(self.APP_LANGUAGE_KEY, DEFAULT_LANGUAGE)
        self._apply_ui_language(language_code)
        enabled_workspaces_raw = db.get_setting(self.APP_ENABLED_WORKSPACES_KEY, "")
        self._apply_workspace_visibility_from_raw(enabled_workspaces_raw)

    def _on_setting_changed(self, key: str, value: str) -> None:
        if key == "app.minimize_on_focus_lost":
            self._minimize_on_focus_lost = value == "1"
            return
        if key == self.APP_LANGUAGE_KEY:
            self._apply_ui_language(value)
            return
        if key == self.APP_ENABLED_WORKSPACES_KEY:
            self._apply_workspace_visibility_from_raw(value)
            return

    def _workspace_mode_map(self) -> dict[str, str]:
        return {
            "projects": self.MODE_PROJECTS,
            "tasks": self.MODE_TASKS,
            "purchases": self.MODE_PURCHASES,
            "ideas": self.MODE_IDEAS,
            "collections": self.MODE_COLLECTIONS,
            "maps": self.MODE_MAPS,
            "notes": self.MODE_NOTES,
            "files": self.MODE_FILES,
            "objects": self.MODE_OBJECTS,
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
            self.MODE_PROJECTS,
            self.MODE_PURCHASES,
            self.MODE_IDEAS,
            self.MODE_COLLECTIONS,
            self.MODE_MAPS,
            self.MODE_NOTES,
            self.MODE_FILES,
            self.MODE_OBJECTS,
            self.MODE_SETTINGS,
        ]
        for mode_name in ordered_modes:
            if self._is_mode_enabled(mode_name):
                return mode_name
        return self.MODE_SETTINGS

    def _mode_caption(self, mode_name: str) -> str:
        return self._mode_labels.get(mode_name, mode_name)

    def _apply_ui_language(self, language_code: str) -> None:
        self._language_code = normalize_language_code(language_code)
        self._mode_labels = get_mode_labels(self._language_code)
        self.left_rail.set_mode_labels(self._mode_labels)
        current_mode = getattr(self, "_current_mode", self.MODE_TASKS)
        mode_caption = self._mode_caption(current_mode)
        self.title_bar.title_label.setText(f"{APP_NAME} В· {mode_caption}")
        self.projects_nav.set_mode_title(mode_caption)

    def _register_system_restore_hotkey(self) -> None:
        self._system_restore_hotkey_registered = False
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            result = ctypes.windll.user32.RegisterHotKey(
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
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()), self._TRAY_RESTORE_HOTKEY_ID)
        finally:
            self._system_restore_hotkey_registered = False

    def _init_tray(self):
        """РќР°СЃС‚СЂР°РёРІР°РµС‚ СЃРёСЃС‚РµРјРЅС‹Р№ С‚СЂРµР№ РґР»СЏ СЃРІРѕСЂР°С‡РёРІР°РЅРёСЏ РїСЂРёР»РѕР¶РµРЅРёСЏ."""
        # РџСЂРѕРІРµСЂСЏРµРј, РґРѕСЃС‚СѓРїРµРЅ Р»Рё СЃРёСЃС‚РµРјРЅС‹Р№ С‚СЂРµР№.
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        # РЎРѕР·РґР°РµРј РёРєРѕРЅРєСѓ С‚СЂРµСЏ Рё РєРѕРЅС‚РµРєСЃС‚РЅРѕРµ РјРµРЅСЋ.
        icon = QIcon(resource_path("assets/icon.ico"))
        self._tray_icon = QSystemTrayIcon(icon, self)
        self._tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        action_show = menu.addAction("РџРѕРєР°Р·Р°С‚СЊ")
        action_quit = menu.addAction("Р’С‹С…РѕРґ")

        # РЎРІСЏР·С‹РІР°РµРј РґРµР№СЃС‚РІРёСЏ РјРµРЅСЋ.
        action_show.triggered.connect(self.restore_from_tray)
        action_quit.triggered.connect(QApplication.instance().quit)

        # РџРѕРґРєР»СЋС‡Р°РµРј РјРµРЅСЋ Рё РѕР±СЂР°Р±РѕС‚С‡РёРє РєР»РёРєРѕРІ РїРѕ РёРєРѕРЅРєРµ.
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.messageClicked.connect(self._on_tray_message_clicked)
        self._tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """РћР±СЂР°Р±Р°С‚С‹РІР°РµС‚ РєР»РёРєРё РїРѕ РёРєРѕРЅРєРµ РІ С‚СЂРµРµ."""
        # РќР° РѕРґРёРЅРѕС‡РЅС‹Р№ РєР»РёРє РІРѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµРј РѕРєРЅРѕ.
        if reason == QSystemTrayIcon.Trigger:
            restore = getattr(self, "restore_from_tray", None)
            if callable(restore):
                restore()
            else:
                self._restore_from_tray()

    def _on_tray_message_clicked(self) -> None:
        task_id = self._tray_message_task_id
        self._tray_message_task_id = None
        restore = getattr(self, "restore_from_tray", None)
        if callable(restore):
            restore()
        else:
            self._restore_from_tray()
        if task_id is not None:
            self._open_task_from_tray_notification(task_id)

    def _open_task_from_tray_notification(self, task_id: int) -> None:
        self.set_mode(self.MODE_TASKS)
        if not hasattr(self.page_tasks, "focus_task"):
            return
        QTimer.singleShot(0, lambda task_id=task_id: self.page_tasks.focus_task(task_id))

    def _restore_from_tray(self):
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РѕРєРЅРѕ РёР· С‚СЂРµСЏ."""
        # Р’РѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµРј СЂРµР¶РёРј РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ РґРѕ СЃРІРѕСЂР°С‡РёРІР°РЅРёСЏ.
        if self.isHidden():
            if self._was_maximized_before_minimize:
                self.showMaximized()
            else:
                self.showNormal()
                if not self._restore_geom.isNull():
                    self.setGeometry(self._restore_geom)
            self._was_maximized_before_minimize = False
        # РџРѕРґРЅРёРјР°РµРј РѕРєРЅРѕ РїРѕРІРµСЂС… Рё СЃРёРЅС…СЂРѕРЅРёР·РёСЂСѓРµРј СЃРѕСЃС‚РѕСЏРЅРёРµ РєРЅРѕРїРєРё.
        self.raise_()
        self.activateWindow()
        self.title_bar.sync_max_button()

    def restore_from_tray(self) -> None:
        self._restore_from_tray()

    def _minimize_to_tray(self):
        """РЎРІРѕСЂР°С‡РёРІР°РµС‚ РѕРєРЅРѕ РІ С‚СЂРµР№."""
        # Р•СЃР»Рё С‚СЂРµР№ РЅРµ СЃРѕР·РґР°РЅ, РІС‹С…РѕРґРёРј Р±РµР· РґРµР№СЃС‚РІРёР№.
        if self._tray_icon is None:
            return
        self._was_maximized_before_minimize = self._was_maximized_before_minimize or self.isMaximized()
        if not self._was_maximized_before_minimize:
            geom = self.normalGeometry() if self.isMinimized() else self.geometry()
            if not geom.isNull() and geom.width() > 0 and geom.height() > 0:
                self._restore_geom = QRect(geom)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        # РџСЂСЏС‡РµРј РѕРєРЅРѕ Рё РїРѕРєР°Р·С‹РІР°РµРј СѓРІРµРґРѕРјР»РµРЅРёРµ.
        self.hide()
        self._tray_message_task_id = None
        self._tray_icon.showMessage(
            APP_NAME,
            "РџСЂРёР»РѕР¶РµРЅРёРµ СЃРІРµСЂРЅСѓС‚Рѕ РІ С‚СЂРµР№.",
            QSystemTrayIcon.Information,
            2000,
        )

    def minimize_to_tray(self) -> None:
        """РЎРІРѕСЂР°С‡РёРІР°РµС‚ РѕРєРЅРѕ: РІ С‚СЂРµР№ РїСЂРё РЅР°Р»РёС‡РёРё, РёРЅР°С‡Рµ СЃС‚Р°РЅРґР°СЂС‚РЅРѕ РІ РїР°РЅРµР»СЊ Р·Р°РґР°С‡."""
        if self._tray_icon is not None:
            self._minimize_to_tray()
            return
        self.showMinimized()

    def _hotkey_defaults_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "defaults" / "hotkeys.default.json"

    def _init_task_reminders(self) -> None:
        """Р—Р°РїСѓСЃРєР°РµС‚ РїРµСЂРёРѕРґРёС‡РµСЃРєРёРµ РЅР°РїРѕРјРёРЅР°РЅРёСЏ Рѕ РїСЂРѕСЃСЂРѕС‡РµРЅРЅС‹С… Р·Р°РґР°С‡Р°С…."""
        self._task_reminder_timer = QTimer(self)
        self._task_reminder_timer.setInterval(60 * 1000)
        self._task_reminder_timer.timeout.connect(self._check_task_reminders)
        self._task_reminder_timer.start()
        QTimer.singleShot(10 * 1000, self._check_task_reminders)

    def _check_task_reminders(self) -> None:
        """РџРѕРєР°Р·С‹РІР°РµС‚ РЅР°РїРѕРјРёРЅР°РЅРёСЏ РєР°Р¶РґС‹Рµ 30 РјРёРЅСѓС‚ РґРѕ РїРµСЂРµРЅРѕСЃР° РёР»Рё РІС‹РїРѕР»РЅРµРЅРёСЏ Р·Р°РґР°С‡Рё."""
        if self._tray_icon is None:
            return
        now = datetime.now()
        due_tasks = []
        active_due_ids: set[int] = set()
        for task in get_database().fetch_tasks():
            if task.done or task.priority == "РћС‚Р»РѕР¶РµРЅРЅР°СЏ":
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
                f"РќР°РїРѕРјРёРЅР°РЅРёРµ Рѕ Р·Р°РґР°С‡Рµ: {task.title}\nРЎСЂРѕРє: {due_text}",
                QSystemTrayIcon.Information,
                5000,
            )
            self._task_remind_next_at[task.id] = now + timedelta(minutes=30)

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
            self.MODE_PURCHASES: "Purchases",
            self.MODE_IDEAS: "Ideas",
            self.MODE_COLLECTIONS: "Collections",
            self.MODE_MAPS: "Maps",
            self.MODE_NOTES: "Notes",
            self.MODE_FILES: "Files",
            self.MODE_OBJECTS: "Objects",
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
            lines.append(f"{binding.sequence} вЂ” {command.title}")
        QMessageBox.information(self, "Р“РѕСЂСЏС‡РёРµ РєР»Р°РІРёС€Рё", "\n".join(lines) or "РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… РіРѕСЂСЏС‡РёС… РєР»Р°РІРёС€")

    def _show_command_palette(self) -> None:
        self._update_hotkey_contexts()
        commands = sorted(self.hotkeys.get_active_hotkeys(), key=lambda item: item[0].title.lower())
        lines = [f"{command.title} ({binding.sequence})" for command, binding in commands]
        QMessageBox.information(self, "Command Palette", "\n".join(lines) or "РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… РєРѕРјР°РЅРґ")

    def _build_ui(self):
        """РЎРѕР·РґР°РµС‚ Рё РєРѕРјРїРѕРЅСѓРµС‚ РѕСЃРЅРѕРІРЅС‹Рµ РІРёРґР¶РµС‚С‹ РѕРєРЅР°."""
        # РљРѕСЂРЅРµРІРѕР№ РєРѕРЅС‚РµР№РЅРµСЂ РѕРєРЅР°.
        outer = QWidget(self)
        outer.setObjectName("OuterRoot")
        self.setCentralWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # РљРѕРЅС‚РµР№РЅРµСЂ РїРѕРґ Р·Р°РіРѕР»РѕРІРѕРє Рё С‚РµР»Рѕ.
        self.container = QWidget()
        self.container.setObjectName("Container")
        outer_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Р’РµСЂС…РЅСЏСЏ РїР°РЅРµР»СЊ Р·Р°РіРѕР»РѕРІРєР°.
        self.title_bar = TitleBar(self)
        self._apply_titlebar_style()

        container_layout.addWidget(self.title_bar)

        # РћСЃРЅРѕРІРЅРѕРµ С‚РµР»Рѕ РѕРєРЅР°.
        body = QWidget()
        body.setObjectName("Body")
        container_layout.addWidget(body, 1)

        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Р›РµРІС‹Р№ rail СЃ РєРЅРѕРїРєР°РјРё СЂРµР¶РёРјРѕРІ.
        self.left_rail = LeftRail()
        body_layout.addWidget(self.left_rail)
        self.left_rail.set_expand_host(body)

        # РљРѕРЅС‚РµР№РЅРµСЂ РєРЅРѕРїРєРё СЃРІРѕСЂР°С‡РёРІР°РЅРёСЏ РЅР°РІРёРіР°С†РёРё.
        self.nav_toggle_container = QWidget()
        self.nav_toggle_container.setObjectName("NavToggleContainer")
        nav_toggle_layout = QVBoxLayout(self.nav_toggle_container)
        nav_toggle_layout.setContentsMargins(0, 0, 0, 0)
        nav_toggle_layout.setSpacing(0)

        # РљРЅРѕРїРєР° СЃРІРѕСЂР°С‡РёРІР°РЅРёСЏ/СЂР°Р·РІРѕСЂР°С‡РёРІР°РЅРёСЏ.
        self.nav_toggle = QToolButton()
        self.nav_toggle.setObjectName("NavToggleButton")
        self.nav_toggle.setText("вџЁ")
        self.nav_toggle.setCursor(Qt.PointingHandCursor)
        self.nav_toggle.setToolTip("РЎРІРµСЂРЅСѓС‚СЊ РЅР°РІРёРіР°С†РёСЋ")

        nav_toggle_layout.addStretch(1)
        nav_toggle_layout.addWidget(self.nav_toggle)
        nav_toggle_layout.addStretch(1)

        body_layout.addWidget(self.nav_toggle_container)

        # РљРѕР»РѕРЅРєР° РЅР°РІРёРіР°С†РёРё Рё РїРѕРёСЃРєР°.
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

        # РЎС‚РµРє СЂР°Р±РѕС‡РёС… РѕР±Р»Р°СЃС‚РµР№.
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        body_layout.addWidget(self.workspace_stack, 1)

        # Pages
        self.page_tasks = TasksWorkspace()
        self.page_projects = ProjectsWorkspace()
        self.page_purchases = PurchasesWorkspace()
        self.page_ideas = IdeasWorkspace()
        self.page_collections = CollectionsWorkspace()
        self.page_maps = MapsListWorkspace()
        self.page_notes = NoteWorkspace()
        self.page_files = FileWorkspace()
        self.page_objects = ObjectWorkspace()
        self.page_settings = SettingsWorkspace()
        self.page_settings.setting_changed.connect(self._on_setting_changed)

        # Р РµРіРёСЃС‚СЂРёСЂСѓРµРј СЃС‚СЂР°РЅРёС†С‹ Рё СЃРѕС…СЂР°РЅСЏРµРј РёС… РёРЅРґРµРєСЃС‹.
        self._page_index = {
            self.MODE_PROJECTS: self.workspace_stack.addWidget(self.page_projects),
            self.MODE_TASKS: self.workspace_stack.addWidget(self.page_tasks),
            self.MODE_PURCHASES: self.workspace_stack.addWidget(self.page_purchases),
            self.MODE_IDEAS: self.workspace_stack.addWidget(self.page_ideas),
            self.MODE_COLLECTIONS: self.workspace_stack.addWidget(self.page_collections),
            self.MODE_MAPS: self.workspace_stack.addWidget(self.page_maps),
            self.MODE_NOTES: self.workspace_stack.addWidget(self.page_notes),
            self.MODE_FILES: self.workspace_stack.addWidget(self.page_files),
            self.MODE_OBJECTS: self.workspace_stack.addWidget(self.page_objects),
            self.MODE_SETTINGS: self.workspace_stack.addWidget(self.page_settings),
        }

        # РџРѕРґРєР»СЋС‡Р°РµРј СЃРёРіРЅР°Р»С‹ РѕС‚ РЅР°РІРёРіР°С†РёРё Рё РїРѕРёСЃРєР°.
        self.projects_nav.filter_changed.connect(self._on_nav_filter_changed)
        self.search_nav.resultActivated.connect(self._on_search_result_activated)
        self._current_mode = self.MODE_TASKS

        # РљРЅРѕРїРєР° СЃРІРѕСЂР°С‡РёРІР°РЅРёСЏ РЅР°РІРёРіР°С†РёРё.
        self.nav_toggle.clicked.connect(self._toggle_nav_column)

        # РџСЂРёРјРµРЅСЏРµРј СЃС‚РёР»Рё Рё СЃРёРЅС…СЂРѕРЅРёР·Р°С†РёСЋ СЂР°Р·РјРµСЂРѕРІ.
        self._apply_root_style()

        self.projects_nav.update_width_for_window(self.width())
        self.search_nav.update_width_for_window(self.width())
        self._set_nav_collapsed(False)

    def _placeholder(self, title: str, subtitle: str) -> QWidget:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РІСЂРµРјРµРЅРЅС‹Р№ СЌРєСЂР°РЅ-Р·Р°РіР»СѓС€РєСѓ РґР»СЏ РЅРµРіРѕС‚РѕРІС‹С… СЂРµР¶РёРјРѕРІ."""
        # Р—Р°РіР»СѓС€РєР° РґР»СЏ СЂРµР¶РёРјРѕРІ Р±РµР· СЂРµР°Р»РёР·Р°С†РёРё.
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
        """РџСЂРёРјРµРЅСЏРµС‚ СЃС‚РёР»Рё Рє Р·Р°РіРѕР»РѕРІРєСѓ РѕРєРЅР°."""
        # РЈСЃС‚Р°РЅР°РІР»РёРІР°РµРј СЃС‚РёР»Рё РґР»СЏ Р·Р°РіРѕР»РѕРІРєР° Рё РєРЅРѕРїРѕРє СѓРїСЂР°РІР»РµРЅРёСЏ.
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
        """РџСЂРёРјРµРЅСЏРµС‚ Р±Р°Р·РѕРІС‹Рµ СЃС‚РёР»Рё Рє РєРѕСЂРЅРµРІРѕРјСѓ РєРѕРЅС‚РµР№РЅРµСЂСѓ."""
        # РџСЂРѕРїРёСЃС‹РІР°РµРј СЃС‚РёР»Рё РґР»СЏ С„РѕРЅР°, РєРѕРЅС‚РµР№РЅРµСЂР° Рё РєРЅРѕРїРєРё РЅР°РІРёРіР°С†РёРё.
        self.centralWidget().setStyleSheet(f"""
            QWidget#OuterRoot {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1c181b, stop:0.5 #101217, stop:0.6001 #101217, stop:1 #101217);
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
        # РџРµСЂРµРґР°РµРј Р°РєС‚РёРІРЅРѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ РЅР°РІРёРіР°С†РёРё РІ СЂР°Р±РѕС‡РёРµ РѕР±Р»Р°СЃС‚Рё.
        if hasattr(workspace, "set_nav_collapsed_state"):
            workspace.set_nav_collapsed_state(not self.nav_column.isVisible())

    def _set_nav_collapsed(self, collapsed: bool) -> None:
        # РЎРєСЂС‹РІР°РµРј/РїРѕРєР°Р·С‹РІР°РµРј РєРѕР»РѕРЅРєСѓ РЅР°РІРёРіР°С†РёРё Рё РјРµРЅСЏРµРј РїРѕРґСЃРєР°Р·РєРё.
        self.nav_column.setVisible(not collapsed)
        self.nav_toggle.setText("вџ©" if collapsed else "вџЁ")
        self.nav_toggle.setToolTip("Р Р°Р·РІРµСЂРЅСѓС‚СЊ РЅР°РІРёРіР°С†РёСЋ" if collapsed else "РЎРІРµСЂРЅСѓС‚СЊ РЅР°РІРёРіР°С†РёСЋ")
        self._apply_nav_state_to_workspace(self.workspace_stack.currentWidget())

    def _toggle_nav_column(self) -> None:
        # РџРµСЂРµРєР»СЋС‡Р°РµРј СЃРѕСЃС‚РѕСЏРЅРёРµ РєРѕР»РѕРЅРєРё РЅР°РІРёРіР°С†РёРё.
        self._set_nav_collapsed(self.nav_column.isVisible())

    def _wire_modes(self):
        """РЎРІСЏР·С‹РІР°РµС‚ РєРЅРѕРїРєРё Р»РµРІРѕРіРѕ РјРµРЅСЋ СЃ СЂРµР¶РёРјР°РјРё СЂР°Р±РѕС‡РёС… РѕР±Р»Р°СЃС‚РµР№."""
        # Р¤РѕСЂРјРёСЂСѓРµРј СЃРѕРѕС‚РІРµС‚СЃС‚РІРёРµ РєРЅРѕРїРѕРє Рё СЂРµР¶РёРјРѕРІ.
        self._btn_to_mode = {
            self.left_rail.btn_projects: self.MODE_PROJECTS,
            self.left_rail.btn_tasks: self.MODE_TASKS,
            self.left_rail.btn_purchases: self.MODE_PURCHASES,
            self.left_rail.btn_ideas: self.MODE_IDEAS,
            self.left_rail.btn_collections: self.MODE_COLLECTIONS,
            self.left_rail.btn_maps: self.MODE_MAPS,
            self.left_rail.btn_notes: self.MODE_NOTES,
            self.left_rail.btn_files: self.MODE_FILES,
            self.left_rail.btn_objects: self.MODE_OBJECTS,
            self.left_rail.btn_settings: self.MODE_SETTINGS,
        }
        self._mode_to_button = {mode_name: button for button, mode_name in self._btn_to_mode.items()}
        # РџРѕРґРєР»СЋС‡Р°РµРј РєР»РёРєРё РЅР° РєРЅРѕРїРєРё Рє СЃРјРµРЅРµ СЂРµР¶РёРјР°.
        for btn, mode in self._btn_to_mode.items():
            btn.clicked.connect(lambda checked=False, m=mode: self.set_mode(m))

    def set_mode(self, mode_name: str):
        """РџРµСЂРµРєР»СЋС‡Р°РµС‚ Р°РєС‚РёРІРЅСѓСЋ СЂР°Р±РѕС‡СѓСЋ РѕР±Р»Р°СЃС‚СЊ Рё РѕР±РЅРѕРІР»СЏРµС‚ Р·Р°РіРѕР»РѕРІРєРё."""
        if not self._is_mode_enabled(mode_name):
            mode_name = self._first_enabled_mode()
        mode_caption = self._mode_caption(mode_name)
        # РћР±РЅРѕРІР»СЏРµРј Р·Р°РіРѕР»РѕРІРѕРє РѕРєРЅР° Рё СЃРѕСЃС‚РѕСЏРЅРёРµ РЅР°РІРёРіР°С†РёРё.
        self.title_bar.title_label.setText(f"{APP_NAME} В· {mode_caption}")
        previous_workspace = self.workspace_stack.currentWidget()
        if previous_workspace is not None and hasattr(previous_workspace, "on_leave"):
            previous_workspace.on_leave()
        self._current_mode = mode_name
        self.projects_nav.set_mode_title(mode_caption)
        # РџРµСЂРµРєР»СЋС‡Р°РµРј СЃС‚СЂР°РЅРёС†Сѓ РІ СЃС‚РµРєРµ.
        self.workspace_stack.setCurrentIndex(self._page_index.get(mode_name, self._page_index[self.MODE_TASKS]))
        self._apply_nav_state_to_workspace(self.workspace_stack.currentWidget())
        current_workspace = self.workspace_stack.currentWidget()
        if current_workspace is not None and hasattr(current_workspace, "on_enter"):
            current_workspace.on_enter(None)
        # РћР±РЅРѕРІР»СЏРµРј РґР°РЅРЅС‹Рµ Р°РєС‚РёРІРЅРѕР№ СЃС‚СЂР°РЅРёС†С‹.
        if mode_name == self.MODE_TASKS:
            self.page_tasks.refresh_tasks()
        elif mode_name == self.MODE_PURCHASES:
            if hasattr(self.page_purchases, "refresh"):
                self.page_purchases.refresh()
        elif mode_name == self.MODE_IDEAS:
            self.page_ideas.refresh()
        elif mode_name == self.MODE_COLLECTIONS:
            self.page_collections.refresh_collections()
        elif mode_name == self.MODE_PROJECTS:
            self.page_projects.refresh_projects()
        elif mode_name == self.MODE_OBJECTS:
            self.page_objects.refresh_objects()

        # РћС‚РјРµС‡Р°РµРј РІС‹Р±СЂР°РЅРЅСѓСЋ РєРЅРѕРїРєСѓ РІ РјРµРЅСЋ.
        for btn, m in self._btn_to_mode.items():
            if m == mode_name:
                btn.setChecked(True)
                break

        self._update_hotkey_contexts()

    def _on_nav_filter_changed(self, kind: str, value: object) -> None:
        # РћРїСЂРµРґРµР»СЏРµРј Р°РєС‚РёРІРЅС‹Р№ СЂРµР¶РёРј Рё РїСЂРѕРєРёРґС‹РІР°РµРј С„РёР»СЊС‚СЂС‹ РІ СЃРѕРѕС‚РІРµС‚СЃС‚РІСѓСЋС‰РёР№ РІРёРґ.
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
        # РџРѕ С‚РёРїСѓ РЅР°Р№РґРµРЅРЅРѕР№ СЃСѓС‰РЅРѕСЃС‚Рё РїРµСЂРµРєР»СЋС‡Р°РµРј РЅСѓР¶РЅС‹Р№ СЂРµР¶РёРј.
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
        elif entity == "collection":
            self.set_mode(self.MODE_COLLECTIONS)
            item_id = payload.get("id")
            if item_id is not None and hasattr(self.page_collections, "focus_item"):
                self.page_collections.focus_item(int(item_id))

    def resizeEvent(self, event):
        """РћР±СЂР°Р±Р°С‚С‹РІР°РµС‚ СЂРµСЃР°Р№Р· РѕРєРЅР°, СЃРёРЅС…СЂРѕРЅРёР·РёСЂСѓСЏ С€РёСЂРёРЅСѓ РЅР°РІРёРіР°С†РёРё."""
        # РџРµСЂРµРґР°РµРј СЃРѕР±С‹С‚РёРµ Р±Р°Р·РѕРІРѕРјСѓ РєР»Р°СЃСЃСѓ Рё РѕР±РЅРѕРІР»СЏРµРј С€РёСЂРёРЅСѓ РїР°РЅРµР»РµР№.
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
        self._unregister_system_restore_hotkey()
        if hasattr(self, "hotkey_store") and hasattr(self, "hotkeys"):
            self.hotkey_store.save(self.hotkeys)
        super().closeEvent(event)

    def nativeEvent(self, event_type, message):
        event_name = (
            bytes(event_type).decode("utf-8", errors="ignore")
            if isinstance(event_type, (bytes, bytearray, memoryview))
            else str(event_type)
        )
        if (
            sys.platform == "win32"
            and getattr(self, "_system_restore_hotkey_registered", False)
            and event_name in {"windows_generic_MSG", "windows_dispatcher_MSG"}
        ):
            try:
                msg = ctypes.cast(message, ctypes.POINTER(_WinMSG)).contents
            except (TypeError, ValueError):
                return super().nativeEvent(event_type, message)
            if msg.message == self._WM_HOTKEY and int(msg.wParam) == self._TRAY_RESTORE_HOTKEY_ID:
                self._restore_from_tray()
                return True, 0
        return super().nativeEvent(event_type, message)

    def changeEvent(self, event):
        """РћР±СЂР°Р±Р°С‚С‹РІР°РµС‚ СЃРІРѕСЂР°С‡РёРІР°РЅРёРµ РѕРєРЅР° РґР»СЏ РѕС‚РїСЂР°РІРєРё РІ С‚СЂРµР№."""
        # РћС‚СЃР»РµР¶РёРІР°РµРј СЃРІРѕСЂР°С‡РёРІР°РЅРёРµ Рё РѕС‚РїСЂР°РІР»СЏРµРј РѕРєРЅРѕ РІ С‚СЂРµР№.
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self._was_maximized_before_minimize = bool(event.oldState() & Qt.WindowState.WindowMaximized)
            self._minimize_to_tray()
            return
        if event.type() == QEvent.Type.ActivationChange:
            app = QApplication.instance()
            app_inactive = app is None or app.applicationState() != Qt.ApplicationState.ApplicationActive
            if (
                app_inactive
                and self._minimize_on_focus_lost
                and self._tray_icon is not None
                and self.isVisible()
                and not self.isHidden()
                and not self.isMinimized()
            ):
                self._minimize_to_tray()

    def keyPressEvent(self, event):
        """РћР±СЂР°Р±Р°С‚С‹РІР°РµС‚ РіРѕСЂСЏС‡РёРµ РєР»Р°РІРёС€Рё РѕРєРЅР°."""
        # Esc Р·Р°РєСЂС‹РІР°РµС‚ РїРѕР»РЅРѕСЌРєСЂР°РЅРЅС‹Р№ СЂРµР¶РёРј РєР°СЂС‚С‹.
        if event.key() == Qt.Key.Key_Escape and self._map_fullscreen_active:
            self.set_map_fullscreen(False)
            event.accept()
            return
        # F11 РїРµСЂРµРєР»СЋС‡Р°РµС‚ РїРѕР»РЅРѕСЌРєСЂР°РЅРЅС‹Р№ СЂРµР¶РёРј РѕРєРЅР°.
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
        """РџСЂРёР»РёРїР°РµС‚ РѕРєРЅРѕ Рє РєСЂР°СЏРј СЌРєСЂР°РЅР° Рё СЂР°Р·РІРѕСЂР°С‡РёРІР°РµС‚ РїСЂРё РєР°СЃР°РЅРёРё РІРµСЂС…РЅРµР№ РіСЂР°РЅРёС†С‹."""
        # Р’ maximized СЂРµР¶РёРј РїСЂРёР»РёРїР°РЅРёРµ РЅРµ РЅСѓР¶РЅРѕ.
        if self.isMaximized():
            return

        # РџРѕР»СѓС‡Р°РµРј Р°РєС‚РёРІРЅС‹Р№ СЌРєСЂР°РЅ Рё РґРѕСЃС‚СѓРїРЅСѓСЋ РіРµРѕРјРµС‚СЂРёСЋ.
        screen = QApplication.screenAt(global_pos) or self.screen()
        geo = screen.availableGeometry()
        t = self.SNAP_THRESHOLD
        x, y = global_pos.x(), global_pos.y()

        # РџСЂРёРєРѕСЃРЅРѕРІРµРЅРёРµ Рє РІРµСЂС…РЅРµРјСѓ РєСЂР°СЋ вЂ” СЂР°Р·РІРѕСЂР°С‡РёРІР°РµРј РѕРєРЅРѕ.
        if abs(y - geo.top()) <= t:
            if self._restore_geom.isNull():
                self._restore_geom = self.geometry()
            self.showMaximized()
            self.title_bar.sync_max_button()
            return

        # РџСЂРёРєРѕСЃРЅРѕРІРµРЅРёРµ Рє Р»РµРІРѕРјСѓ РєСЂР°СЋ вЂ” РїРѕР»РѕРІРёРЅРЅРѕРµ РѕРєРЅРѕ СЃР»РµРІР°.
        if abs(x - geo.left()) <= t:
            self.setGeometry(QRect(geo.left(), geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

        # РџСЂРёРєРѕСЃРЅРѕРІРµРЅРёРµ Рє РїСЂР°РІРѕРјСѓ РєСЂР°СЋ вЂ” РїРѕР»РѕРІРёРЅРЅРѕРµ РѕРєРЅРѕ СЃРїСЂР°РІР°.
        if abs(x - geo.right()) <= t:
            self.setGeometry(QRect(geo.left() + geo.width() // 2, geo.top(), geo.width() // 2, geo.height()))
            self._restore_geom = self.geometry()
            return

    def snap_to_screen_edges(self, global_pos: QPoint) -> None:
        self._snap_to_screen_edges(global_pos)

    def _begin_restore_on_drag(self, global_pos: QPoint):
        """Р’РѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ РЅРѕСЂРјР°Р»СЊРЅС‹Р№ СЂР°Р·РјРµСЂ РїСЂРё РїРµСЂРµС‚Р°СЃРєРёРІР°РЅРёРё РёР· maximize."""
        # Р•СЃР»Рё РЅРµ maximized, РЅРёС‡РµРіРѕ РЅРµ РґРµР»Р°РµРј.
        if not self.isMaximized():
            return

        # Р—Р°РїРѕРјРёРЅР°РµРј РіРµРѕРјРµС‚СЂРёСЋ РѕРєРЅР° РґРѕ maximized.
        if self._restore_geom.isNull():
            self._restore_geom = self.normalGeometry()

        # Р Р°СЃСЃС‡РёС‚С‹РІР°РµРј РѕС‚РЅРѕСЃРёС‚РµР»СЊРЅСѓСЋ РїРѕР·РёС†РёСЋ РєСѓСЂСЃРѕСЂР° РїРѕ СЌРєСЂР°РЅСѓ.
        screen = QApplication.screenAt(global_pos) or self.screen()
        avail = screen.availableGeometry()
        rel_x = (global_pos.x() - avail.left()) / max(1, avail.width())
        rel_x = min(max(rel_x, 0.05), 0.95)

        # Р’РѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµРј РѕРєРЅРѕ Рё РїРµСЂРµСЃС‡РёС‚С‹РІР°РµРј РіРµРѕРјРµС‚СЂРёСЋ РїРѕРґ РєСѓСЂСЃРѕСЂРѕРј.
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
        """РћРїСЂРµРґРµР»СЏРµС‚, Р·Р° РєР°РєРѕР№ РєСЂР°Р№ РѕРєРЅР° РѕС‚РІРµС‡Р°РµС‚ С‚РµРєСѓС‰Р°СЏ РїРѕР·РёС†РёСЏ РјС‹С€Рё."""
        # Р’ maximized СЂРµР¶РёРјРµ СЂРµСЃР°Р№Р· РѕС‚РєР»СЋС‡РµРЅ.
        if self.isMaximized():
            return ResizeEdge.NONE

        # РћРїСЂРµРґРµР»СЏРµРј РЅР°РїСЂР°РІР»РµРЅРёРµ СЂРµСЃР°Р№Р·Р° РїРѕ РєРѕРѕСЂРґРёРЅР°С‚Р°Рј.
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
        """Return cursor shape for selected resize edge."""
        # Select cursor icon for current resize edge orientation.
        diagonal_forward = {
            ResizeEdge.TOP | ResizeEdge.LEFT,
            ResizeEdge.BOTTOM | ResizeEdge.RIGHT,
        }
        diagonal_backward = {
            ResizeEdge.TOP | ResizeEdge.RIGHT,
            ResizeEdge.BOTTOM | ResizeEdge.LEFT,
        }
        if edge in (ResizeEdge.LEFT, ResizeEdge.RIGHT):
            return Qt.CursorShape.SizeHorCursor
        if edge in (ResizeEdge.TOP, ResizeEdge.BOTTOM):
            return Qt.CursorShape.SizeVerCursor
        if edge in diagonal_forward:
            return Qt.CursorShape.SizeFDiagCursor
        if edge in diagonal_backward:
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _start_resize(self, edge: ResizeEdge, global_pos: QPoint):
        """РЎС‚Р°СЂС‚СѓРµС‚ РѕРїРµСЂР°С†РёСЋ РёР·РјРµРЅРµРЅРёСЏ СЂР°Р·РјРµСЂРѕРІ РѕРєРЅР°."""
        # РЎРѕС…СЂР°РЅСЏРµРј РїР°СЂР°РјРµС‚СЂС‹ СЃС‚Р°СЂС‚Р° СЂРµСЃР°Р№Р·Р°.
        self._resizing = True
        self._resize_edge = edge
        self._press_global = global_pos
        self._start_geom = self.geometry()

    def _do_resize(self, global_pos: QPoint):
        """Р’С‹РїРѕР»РЅСЏРµС‚ РёР·РјРµРЅРµРЅРёРµ РіРµРѕРјРµС‚СЂРёРё РѕРєРЅР° РІРѕ РІСЂРµРјСЏ СЂРµСЃР°Р№Р·Р°."""
        # Р•СЃР»Рё СЂРµСЃР°Р№Р· РЅРµ Р°РєС‚РёРІРµРЅ, РЅРёС‡РµРіРѕ РЅРµ РґРµР»Р°РµРј.
        if not self._resizing or self._resize_edge == ResizeEdge.NONE:
            return

        # Р Р°СЃСЃС‡РёС‚С‹РІР°РµРј СЃРјРµС‰РµРЅРёСЏ РєСѓСЂСЃРѕСЂР°.
        dx = global_pos.x() - self._press_global.x()
        dy = global_pos.y() - self._press_global.y()

        g = QRect(self._start_geom)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        # РћР±РЅРѕРІР»СЏРµРј РіСЂР°РЅРёС†С‹ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РЅР°РїСЂР°РІР»РµРЅРёСЏ СЂРµСЃР°Р№Р·Р°.
        if (self._resize_edge & ResizeEdge.LEFT) != ResizeEdge.NONE:
            new_x = g.x() + dx
            new_w = g.width() - dx
            if new_w >= min_w:
                g.setX(new_x)
                g.setWidth(new_w)

        if (self._resize_edge & ResizeEdge.RIGHT) != ResizeEdge.NONE:
            new_w = g.width() + dx
            if new_w >= min_w:
                g.setWidth(new_w)

        if (self._resize_edge & ResizeEdge.TOP) != ResizeEdge.NONE:
            new_y = g.y() + dy
            new_h = g.height() - dy
            if new_h >= min_h:
                g.setY(new_y)
                g.setHeight(new_h)

        if (self._resize_edge & ResizeEdge.BOTTOM) != ResizeEdge.NONE:
            new_h = g.height() + dy
            if new_h >= min_h:
                g.setHeight(new_h)

        # РџСЂРёРјРµРЅСЏРµРј РЅРѕРІСѓСЋ РіРµРѕРјРµС‚СЂРёСЋ Рё Р·Р°РїРѕРјРёРЅР°РµРј РµРµ.
        self.setGeometry(g)
        self._restore_geom = self.geometry()

    def _stop_resize(self):
        """РЎР±СЂР°СЃС‹РІР°РµС‚ СЃРѕСЃС‚РѕСЏРЅРёРµ РёР·РјРµРЅРµРЅРёСЏ СЂР°Р·РјРµСЂРѕРІ."""
        # РЎР±СЂР°СЃС‹РІР°РµРј С„Р»Р°РіРё СЂРµСЃР°Р№Р·Р°.
        self._resizing = False
        self._resize_edge = ResizeEdge.NONE

    def eventFilter(self, obj, event):
        """РџРµСЂРµС…РІР°С‚С‹РІР°РµС‚ СЃРѕР±С‹С‚РёСЏ РјС‹С€Рё РґР»СЏ РєР°СЃС‚РѕРјРЅРѕРіРѕ СЂРµСЃР°Р№Р·Р°."""
        # РћР±СЂР°Р±Р°С‚С‹РІР°РµРј СЃРѕР±С‹С‚РёСЏ С‚РѕР»СЊРєРѕ РґР»СЏ СЃР°РјРѕРіРѕ РѕРєРЅР°.
        if obj is self:
            # рџ”Ґ Р’ maximized РїРѕР»РЅРѕСЃС‚СЊСЋ РІС‹РєР»СЋС‡Р°РµРј hit-test Рё РґРµСЂРіР°РЅРёРµ РєСѓСЂСЃРѕСЂР°
            if self.isMaximized():
                if event.type() in (event.Type.MouseMove, event.Type.Leave):
                    self.unsetCursor()
                return super().eventFilter(obj, event)

            if event.type() == event.Type.MouseMove:
                pos = event.position().toPoint()
                global_pos = event.globalPosition().toPoint()

                # Р’Рѕ РІСЂРµРјСЏ СЂРµСЃР°Р№Р·Р° РјРµРЅСЏРµРј РіРµРѕРјРµС‚СЂРёСЋ.
                if self._resizing:
                    self._do_resize(global_pos)
                    return True

                # РћР±РЅРѕРІР»СЏРµРј РєСѓСЂСЃРѕСЂ, РµСЃР»Рё РёР·РјРµРЅРёР»СЃСЏ РєСЂР°Р№ СЂРµСЃР°Р№Р·Р°.
                edge = self._hit_test_edges(pos)
                if edge != self._resize_edge:
                    self._resize_edge = edge
                    self.setCursor(self._cursor_for_edge(edge))
                return False

            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    pos = event.position().toPoint()
                    edge = self._hit_test_edges(pos)
                    if edge != ResizeEdge.NONE:
                        # Р—Р°РїСѓСЃРєР°РµРј СЂРµСЃР°Р№Р· РїСЂРё РЅР°Р¶Р°С‚РёРё РЅР° РєСЂР°Р№.
                        self._start_resize(edge, event.globalPosition().toPoint())
                        return True
                return False

            if event.type() == event.Type.MouseButtonRelease:
                # РћСЃС‚Р°РЅР°РІР»РёРІР°РµРј СЂРµСЃР°Р№Р· РїРѕ РѕС‚РїСѓСЃРєР°РЅРёСЋ.
                if self._resizing:
                    self._stop_resize()
                    return True
                return False

            if event.type() == event.Type.Leave:
                # Р’РѕР·РІСЂР°С‰Р°РµРј РєСѓСЂСЃРѕСЂ, РµСЃР»Рё РЅРµ СЂРµСЃР°Р№Р·РёРј.
                if not self._resizing:
                    self.unsetCursor()
                return False

        return super().eventFilter(obj, event)

    def set_map_fullscreen(self, enabled: bool) -> None:
        # РќРµ РІС‹РїРѕР»РЅСЏРµРј РґРµР№СЃС‚РІРёСЏ, РµСЃР»Рё СЃРѕСЃС‚РѕСЏРЅРёРµ РЅРµ РёР·РјРµРЅРёР»РѕСЃСЊ.
        if self._map_fullscreen_active == enabled:
            return
        self._map_fullscreen_active = enabled
        if enabled:
            # Р—Р°РїРѕРјРёРЅР°РµРј РІРёРґРёРјРѕСЃС‚СЊ РїР°РЅРµР»РµР№ Рё СЃРєСЂС‹РІР°РµРј РёС….
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
            # Р’РѕР·РІСЂР°С‰Р°РµРј РІРёРґРёРјРѕСЃС‚СЊ РїР°РЅРµР»РµР№ Рё СЂРµР¶РёРј РѕРєРЅР°.
            self.title_bar.setVisible(self._map_fullscreen_restore.get("title_bar", True))
            self.left_rail.setVisible(self._map_fullscreen_restore.get("left_rail", True))
            self.nav_toggle_container.setVisible(self._map_fullscreen_restore.get("nav_toggle", True))
            self.nav_column.setVisible(self._map_fullscreen_restore.get("nav_column", True))
            if self._was_maximized_before_fullscreen:
                self.showMaximized()
            else:
                self.showNormal()
            self.title_bar.sync_max_button()
        # РЎРѕРѕР±С‰Р°РµРј СЂР°Р±РѕС‡РµР№ РѕР±Р»Р°СЃС‚Рё Рѕ СЃРјРµРЅРµ РїРѕР»РЅРѕСЌРєСЂР°РЅРЅРѕРіРѕ СЂРµР¶РёРјР°.
        self.page_maps.set_map_fullscreen_state(enabled)

