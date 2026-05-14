from __future__ import annotations

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

import mindnavigator.ui.splash as splash_module


def test_splash_widget_accepts_preloaded_pixmap() -> None:
    _app = QApplication.instance() or QApplication([])
    pixmap = QPixmap(64, 40)
    pixmap.fill(QColor("#336699"))

    splash = splash_module.SplashWidget(_app, pixmap, w=220, h=140)
    try:
        current = splash.image_label.pixmap()
        assert current is not None
        assert current.isNull() is False
    finally:
        splash.close()
        splash.deleteLater()


def test_show_splash_preloads_image_before_show(monkeypatch, tmp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "splash.png"
    pixmap = QPixmap(48, 48)
    pixmap.fill(QColor("#884422"))
    assert pixmap.save(str(image_path), "PNG")

    monkeypatch.setattr(splash_module, "resource_path", lambda path: str(image_path))

    splash = splash_module.show_splash(_app, "ignored.png")
    try:
        current = splash.image_label.pixmap()
        assert current is not None
        assert current.isNull() is False
    finally:
        splash.close()
        splash.deleteLater()
