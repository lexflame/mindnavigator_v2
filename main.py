"""Точка входа приложения MindNavigator.

Входные данные:
    Аргументы командной строки из sys.argv.

Выходные данные:
    Код завершения процесса приложения.
"""

import sys
from functools import partial

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer

from mindnavigator.constants import APP_NAME
from mindnavigator.resources import resource_path
from mindnavigator.ui.splash import show_splash
from mindnavigator.main_window import MainWindow
from mindnavigator.storage import get_database
from mindnavigator.ui.styles import APP_STYLESHEET


def _connect_shutdown_handlers(app: QApplication) -> None:
    """Подключает обработчики корректного завершения приложения.

    Входные данные:
        app: Экземпляр QApplication для доступа к сигналу завершения.

    Выходные данные:
        None. Функция регистрирует обработчики и не возвращает значение.
    """

    def close_database() -> None:
        """Закрывает соединение с базой данных при завершении приложения.

        Входные данные:
            Нет.

        Выходные данные:
            None. Закрывает соединение при наличии активного кэша.
        """
        if get_database.cache_info().currsize:
            get_database().close()

    app.aboutToQuit.connect(close_database)


def main() -> None:
    """Запускает приложение и управляет стартовой инициализацией.

    Входные данные:
        Нет (используется sys.argv).

    Выходные данные:
        None. Завершает процесс с кодом завершения приложения.
    """
    # Отключаем использование высокоразрешающих пиктограмм (для слабых GPU/старых драйверов)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    app.setQuitOnLastWindowClosed(False)

    app.setStyleSheet(APP_STYLESHEET)
    _connect_shutdown_handlers(app)

    # Показываем заставку
    splash = show_splash(app, resource_path("assets/splash.jpg"))
    splash.set_status("Инициализация интерфейса…")

    # Создаём главное окно
    window = MainWindow()

    # Этапы загрузки с задержками
    startup_steps = [
        (150, "Подготовка модулей…"),
        (300, "Загрузка проекта…"),
        (450, "Проверка хранилища…"),
        (600, "Готово."),
    ]

    for delay_ms, status_text in startup_steps:
        QTimer.singleShot(delay_ms, partial(splash.set_status, status_text))

    def finish_startup() -> None:
        """Завершает стартовый процесс: показывает главное окно и закрывает заставку.

        Входные данные:
            Нет.

        Выходные данные:
            None. Выполняет показ окна и закрытие заставки.
        """
        window.show()
        # Используем один таймер для последовательных действий
        QTimer.singleShot(0, lambda: (
            window.showMaximized(),
            window.title_bar.sync_max_button()
        ))
        splash.close()

    finish_startup()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
