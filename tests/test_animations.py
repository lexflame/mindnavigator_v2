from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsOpacityEffect, QWidget

from mindnavigator.ui.animations import (
    DialogAppearAnimationConfig,
    DialogAppearAnimator,
    DialogMinimizeAnimationConfig,
    DialogMinimizeAnimator,
    WidthExpandAnimationConfig,
    normalize_duration_ms,
    normalize_width_bounds,
)
from mindnavigator.ui.modals import DialogPresentationController, ModalOverlay, show_dialog_standard


def test_normalize_width_bounds_clamps_and_orders() -> None:
    collapsed, expanded = normalize_width_bounds(-10, 5)
    assert collapsed == 1
    assert expanded == 5

    collapsed, expanded = normalize_width_bounds(220, 80)
    assert collapsed == 220
    assert expanded == 220


def test_normalize_duration_ms_clamps_minimum() -> None:
    assert normalize_duration_ms(-1) == 1
    assert normalize_duration_ms(0) == 1
    assert normalize_duration_ms(120) == 120


def test_width_expand_config_normalized() -> None:
    config = WidthExpandAnimationConfig(collapsed_width=0, expanded_width=10, duration_ms=0).normalized()
    assert config.collapsed_width == 1
    assert config.expanded_width == 10
    assert config.duration_ms == 1


def test_dialog_appear_config_normalized() -> None:
    config = DialogAppearAnimationConfig(
        duration_ms=0,
        offset_px=-20,
        inset_px=-5,
        start_opacity=-1.0,
        end_opacity=4.0,
    ).normalized()
    assert config.duration_ms == 1
    assert config.offset_px == 0
    assert config.inset_px == 0
    assert config.start_opacity == 0.0
    assert config.end_opacity == 1.0


def test_dialog_appear_animator_builds_slightly_smaller_lower_start_rect() -> None:
    config = DialogAppearAnimationConfig(duration_ms=180, offset_px=10, inset_px=10).normalized()
    target_rect = QRect(100, 120, 500, 320)
    start_rect = DialogAppearAnimator._build_start_rect(target_rect, config)

    assert start_rect.width() == 480
    assert start_rect.height() == 300
    assert start_rect.left() == 110
    assert start_rect.top() == 140


def test_dialog_minimize_config_normalized() -> None:
    config = DialogMinimizeAnimationConfig(
        duration_ms=0,
        offset_px=-10,
        inset_px=-5,
        start_opacity=4.0,
        end_opacity=-1.0,
    ).normalized()
    assert config.duration_ms == 1
    assert config.offset_px == 0
    assert config.inset_px == 0
    assert config.start_opacity == 1.0
    assert config.end_opacity == 0.0


def test_dialog_minimize_animator_builds_lower_smaller_end_rect() -> None:
    config = DialogMinimizeAnimationConfig(duration_ms=150, offset_px=56, inset_px=12).normalized()
    start_rect = QRect(100, 120, 500, 320)
    end_rect = DialogMinimizeAnimator._build_end_rect(start_rect, config)

    assert end_rect.width() == 476
    assert end_rect.height() == 296
    assert end_rect.left() == 112
    assert end_rect.top() == 188


class _ProbeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.exec_calls = 0

    def exec(self) -> int:  # noqa: A003 - Qt compatibility
        self.exec_calls += 1
        self.done(QDialog.DialogCode.Accepted)
        return int(QDialog.DialogCode.Accepted)


def test_dialog_presentation_controller_adds_dialog_appear_effect() -> None:
    _app = QApplication.instance() or QApplication([])
    parent = QWidget()
    dialog = QDialog(parent)
    controller = DialogPresentationController()
    try:
        overlay = controller.prepare(dialog, parent=parent)
        QApplication.processEvents()
        assert overlay is not None
        assert isinstance(dialog.graphicsEffect(), QGraphicsOpacityEffect)
    finally:
        dialog.deleteLater()
        parent.deleteLater()


def test_show_dialog_standard_prepares_dialog_when_global_patch_is_disabled() -> None:
    _app = QApplication.instance() or QApplication([])
    parent = QWidget()
    dialog = _ProbeDialog(parent)
    try:
        result = show_dialog_standard(dialog, parent)
        QApplication.processEvents()
        assert result == int(QDialog.DialogCode.Accepted)
        assert dialog.exec_calls == 1
        assert isinstance(dialog.graphicsEffect(), QGraphicsOpacityEffect)
    finally:
        dialog.deleteLater()
        parent.deleteLater()


def test_modal_overlay_invokes_direct_click_handler() -> None:
    _app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(300, 200)
    overlay = ModalOverlay(parent)
    calls = []
    setattr(overlay, "_overlay_click_handler", lambda: calls.append("clicked"))
    try:
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            overlay.rect().center(),
            overlay.mapToGlobal(overlay.rect().center()),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        overlay.mousePressEvent(event)
        assert calls == ["clicked"]
    finally:
        overlay.deleteLater()
        parent.deleteLater()
