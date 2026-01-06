import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer

from mindnavigator.constants import APP_NAME
from mindnavigator.ui.splash import show_splash
from mindnavigator.main_window import MainWindow


def main():
    # Hardcore: can help on weak GPU / old drivers
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon("assets/icon.png"))

    splash = show_splash(app, "assets/splash.png")
    splash.set_status("Инициализация интерфейса…")

    window = MainWindow()

    steps = [
        (150, "Подготовка модулей…"),
        (300, "Загрузка проекта…"),
        (450, "Проверка хранилища…"),
        (600, "Готово."),
    ]
    for ms, text in steps:
        QTimer.singleShot(ms, lambda t=text: splash.set_status(t))

    def finish_start():
        window.show()
        splash.close()

    QTimer.singleShot(750, finish_start)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
