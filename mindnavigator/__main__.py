"""Пакетная точка входа MindNavigator (`python -m mindnavigator`)."""

from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .constants import APP_NAME
from .resources import resource_path
from .ui.splash import show_splash
from .main_window import MainWindow
from .storage import get_database
from .ui.dialogs.frameless_patch import enable_frameless_qdialogs
from .ui.styles import APP_STYLESHEET


class _SingleInstanceBridge(QObject):
    def __init__(self, server_name: str) -> None:
        super().__init__()
        self._server_name = server_name
        self._server: QLocalServer | None = None
        self._on_message = None

    def notify_existing(self, message: str) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(200):
            return False
        socket.write(message.encode("utf-8"))
        socket.waitForBytesWritten(200)
        socket.disconnectFromServer()
        return True

    def start(self) -> bool:
        QLocalServer.removeServer(self._server_name)
        server = QLocalServer(self)
        if not server.listen(self._server_name):
            return False
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def set_callback(self, callback) -> None:
        self._on_message = callback

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.waitForReadyRead(200)
            raw_payload = socket.readAll()
            payload = bytes(raw_payload.data()).decode("utf-8", errors="ignore").strip()
            socket.disconnectFromServer()
            if self._on_message is not None and payload:
                self._on_message(payload)


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
    db = get_database()
    single_instance_enabled = db.get_setting("app.single_instance", "1") == "1"
    single_instance_bridge: _SingleInstanceBridge | None = None
    if single_instance_enabled:
        single_instance_bridge = _SingleInstanceBridge("mindnavigator_v2.instance")
        if single_instance_bridge.notify_existing("restore"):
            return
        single_instance_bridge.start()

    splash = show_splash(app, resource_path("assets/splash.jpg"))
    splash.set_status("Инициализация интерфейса…")
    splash.raise_()
    splash.fade_in()

    window = MainWindow()
    if single_instance_bridge is not None:
        single_instance_bridge.set_callback(lambda _msg: window.restore_from_tray())
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
