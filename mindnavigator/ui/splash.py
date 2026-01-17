"""Заставка приложения и функции её показа.

Входные данные:
    Экземпляр QApplication и путь к изображению заставки.

Выходные данные:
    Виджет заставки и обновлённые статусы загрузки.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from ..resources import resource_path


class SplashWidget(QWidget):
    """Быстрая заставка без прозрачности и анимаций."""

    def __init__(self, app: QApplication, image_path: str, w: int = 460, h: int = 280):
        """Создает виджет заставки и подготавливает содержимое."""
        super().__init__(None)
        self._app = app

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(w, h)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("SplashCard")
        root.addWidget(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 14, 14, 12)
        card_layout.setSpacing(10)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        pm = QPixmap(image_path)
        if not pm.isNull():
            pm2 = pm.scaled(w - 28, h - 70, Qt.KeepAspectRatio, Qt.FastTransformation)
            self.image_label.setPixmap(pm2)

        self.status_label = QLabel("Запуск…")
        self.status_label.setObjectName("SplashStatus")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        card_layout.addWidget(self.image_label, 1)
        card_layout.addWidget(self.status_label, 0)

        self.setStyleSheet("""
            QFrame#SplashCard {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
            QLabel#SplashStatus {
                color: #a8a8a8;
                font-size: 12px;
                padding-left: 2px;
            }
        """)

    def center_on_screen(self):
        """Центрирует заставку на активном экране."""
        screen = self._app.primaryScreen().availableGeometry()
        r = self.frameGeometry()
        r.moveCenter(screen.center())
        self.move(r.topLeft())

    def set_status(self, text: str):
        """Обновляет текст статуса и принудительно обрабатывает события."""
        self.status_label.setText(text)
        self._app.processEvents()


def show_splash(app: QApplication, image_path: str = "assets/splash.jpg") -> SplashWidget:
    """Показывает заставку и возвращает её объект."""
    splash = SplashWidget(app, resource_path(image_path), w=460, h=280)
    splash.center_on_screen()
    splash.show()
    app.processEvents()
    return splash
