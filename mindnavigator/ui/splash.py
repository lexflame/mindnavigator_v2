"""Splash screen widget and show helper."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from mindnavigator.spaceenity.resources import resource_path


class SplashWidget(QWidget):
    """Fast splash screen with a preloaded image."""

    def __init__(self, app: QApplication, image_source: str | QPixmap, w: int = 460, h: int = 280):
        super().__init__(None)
        self._app = app

        self.setWindowFlags(
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(w, h)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

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
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pm = image_source if isinstance(image_source, QPixmap) else QPixmap(image_source)
        if not pm.isNull():
            scaled = pm.scaled(
                w - 28,
                h - 70,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.image_label.setPixmap(scaled)

        self.status_label = QLabel("Запуск…")
        self.status_label.setObjectName("SplashStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(self.image_label, 1)
        card_layout.addWidget(self.status_label, 0)

        self.setStyleSheet(
            """
            QFrame#SplashCard {
                background: #16171a;
                border: 1px solid #2a2b2f;
            }
            QLabel#SplashStatus {
                color: #a8a8a8;
                font-size: 12px;
                padding-left: 2px;
            }
            """
        )

    def fade_in(self) -> None:
        self.animation.stop()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def fade_out(self, on_finished=None) -> None:
        self.animation.stop()
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        if on_finished:
            self.animation.finished.connect(on_finished)
        self.animation.start()

    def center_on_screen(self) -> None:
        screen = self._app.primaryScreen().availableGeometry()
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.center())
        self.move(geometry.topLeft())

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self._app.processEvents()


def show_splash(app: QApplication, image_path: str = "assets/splash.jpg") -> SplashWidget:
    """Show splash screen using a pixmap loaded before the widget is shown."""
    splash_pixmap = QPixmap(resource_path(image_path))
    splash = SplashWidget(app, splash_pixmap, w=460, h=280)
    splash.center_on_screen()
    splash.show()
    app.processEvents()
    return splash
