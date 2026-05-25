from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from mindnavigator.ui.leftrail import LeftRail


def _show_left_rail() -> tuple[QWidget, LeftRail]:
    _app = QApplication.instance() or QApplication([])
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    rail = LeftRail(host)
    layout.addWidget(rail)
    host.resize(320, 900)
    host.show()
    QApplication.processEvents()
    return host, rail


def test_left_rail_utility_buttons_are_centered_and_do_not_overlap() -> None:
    host, rail = _show_left_rail()
    try:
        mode_center_x = rail.btn_tasks.geometry().center().x()

        for button in (rail.btn_hotkeys_help, rail.btn_theme_toggle, rail.btn_settings):
            assert button.geometry().center().x() == mode_center_x
            assert button.width() == 36
            assert button.height() == 36

        assert rail.btn_hotkeys_help.geometry().bottom() < rail.btn_theme_toggle.geometry().top()
        assert rail.btn_theme_toggle.geometry().bottom() < rail.btn_settings.geometry().top()
        assert rail.btn_hotkeys_help.geometry().intersects(rail.btn_theme_toggle.geometry()) is False
        assert rail.btn_theme_toggle.geometry().intersects(rail.btn_settings.geometry()) is False
    finally:
        host.close()


def test_left_rail_theme_toggle_click_does_not_trigger_settings_or_help() -> None:
    host, rail = _show_left_rail()
    try:
        theme_modes: list[str] = []
        settings_clicks: list[bool] = []
        help_clicks: list[bool] = []

        rail.theme_toggled.connect(theme_modes.append)
        rail.btn_settings.clicked.connect(lambda checked=False: settings_clicks.append(bool(checked)))
        rail.hotkeys_help_requested.connect(lambda: help_clicks.append(True))

        QTest.mouseClick(rail.btn_theme_toggle, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert theme_modes == ["light"]
        assert settings_clicks == []
        assert help_clicks == []
        assert rail.btn_settings.isChecked() is False
        assert rail.btn_tasks.isChecked() is True
    finally:
        host.close()


def test_left_rail_hotkeys_button_emits_help_signal_only() -> None:
    host, rail = _show_left_rail()
    try:
        help_clicks: list[bool] = []
        theme_modes: list[str] = []

        rail.hotkeys_help_requested.connect(lambda: help_clicks.append(True))
        rail.theme_toggled.connect(theme_modes.append)

        QTest.mouseClick(rail.btn_hotkeys_help, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

        assert help_clicks == [True]
        assert theme_modes == []
        assert rail.btn_settings.isChecked() is False
        assert rail.btn_tasks.isChecked() is True
    finally:
        host.close()
