"""Пакетная точка входа MindNavigator (`python -m mindnavigator`)."""

from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

from .constants import APP_NAME
from .resources import resource_path
from .ui.splash import show_splash
from .main_window import MainWindow
from .storage import get_database
from .ui.dialogs.frameless_patch import enable_frameless_qdialogs
from .ui.styles import APP_STYLESHEET


def _connect_shutdown_handlers(app: QApplication) -> None:
    def close_database() -> None:
        if get_database.cache_info().currsize:
            get_database().close()

    app.aboutToQuit.connect(close_database)


def main() -> None:
    enable_frameless_qdialogs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(APP_STYLESHEET)
    _connect_shutdown_handlers(app)

    splash = show_splash(app, resource_path("assets/splash.jpg"))
    splash.set_status("Инициализация интерфейса…")
    splash.raise_()
    splash.fade_in()

    window = MainWindow()
    startup_steps = [
        "Подготовка модулей…",
        "Загрузка проекта…",
        "Проверка хранилища…",
        "Готово.",
    ]

    def show_next_status(step_index: int) -> None:
        if step_index >= len(startup_steps):
            finish_startup()
            return
        splash.set_status(startup_steps[step_index])
        next_index = step_index + 1
        if next_index < len(startup_steps):
            delay_ms = 150 if step_index == 0 else 300
            QTimer.singleShot(delay_ms, lambda: show_next_status(next_index))
        else:
            QTimer.singleShot(400, lambda: show_next_status(next_index))

    def finish_startup() -> None:
        window.show()
        QTimer.singleShot(0, lambda: (window.showMaximized(), window.title_bar.sync_max_button()))
        splash.close()

    show_next_status(0)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
