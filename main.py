import sys
from functools import partial

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer

from mindnavigator.constants import APP_NAME
from mindnavigator.ui.splash import show_splash
from mindnavigator.main_window import MainWindow


def main():
    """Запускает приложение и управляет стартовой инициализацией."""
    # Hardcore: может помочь на слабых GPU / старых драйверах
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon("assets/icon.png"))
    app.setStyleSheet("""
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
    """)

    splash = show_splash(app, "assets/splash.png")
    splash.set_status("Инициализация интерфейса…")

    window = MainWindow()

    steps = (
        (150, "Подготовка модулей…"),
        (300, "Загрузка проекта…"),
        (450, "Проверка хранилища…"),
        (600, "Готово."),
    )
    for ms, text in steps:
        QTimer.singleShot(ms, partial(splash.set_status, text))

    def finish_start():
        """Показывает главное окно и закрывает заставку."""
        window.show()
        QTimer.singleShot(0, window.showMaximized)
        QTimer.singleShot(0, window.title_bar.sync_max_button)
        splash.close()

    finish_start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
