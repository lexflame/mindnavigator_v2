import sys
from functools import partial

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer

from mindnavigator.constants import APP_NAME
from mindnavigator.resources import resource_path
from mindnavigator.ui.splash import show_splash
from mindnavigator.main_window import MainWindow



def main():
    """Запускает приложение и управляет стартовой инициализацией."""
    # Отключаем использование высокоразрешающих пиктограмм (для слабых GPU/старых драйверов)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    app.setQuitOnLastWindowClosed(False)

    # Выносим стили в отдельную константу для лучшей читаемости
    APP_STYLESHEET = """
        QMessageBox {
            background: #16171a;
        }
        QMessageBox QLabel {
            color: #cfcfcf;
        }
        QMessageBox QPushButton {
            background: #2a2b2f;
            color: #e6e6e6;
            border: 1px solid #3a3b40;
            padding: 6px 12px;
            border-radius: 6px;
            min-width: 90px;
        }
        QMessageBox QPushButton:hover {
            background: #34363b;
        }
        QComboBox::drop-down {
            border: none;
            width: 18px;
        }
        QComboBox QAbstractItemView {
            background: #1c1d22;
            color: #e6e6e6;
            border: 1px solid #2a2b2f;
            selection-background-color: #2f3238;
            selection-color: #f2f2f2;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            padding: 6px 10px;
        }
        QComboBox QAbstractItemView::item:selected {
            background: #2f3238;
            color: #f2f2f2;
        }
        QMenu {
            background: #1f2227;
            color: #e6e6e6;
            border: 1px solid #2a2b2f;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 14px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background: #2b2f36;
        }
        QMenu::separator {
            height: 1px;
            background: #2a2b2f;
            margin: 4px 8px;
        }
    """
    app.setStyleSheet(APP_STYLESHEET)

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

    def finish_startup():
        """Завершает стартовый процесс: показывает главное окно и закрывает заставку."""
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
