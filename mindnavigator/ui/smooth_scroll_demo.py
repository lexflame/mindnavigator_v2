from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from mindnavigator.ui.smooth_scroll import SmoothScrollConfig, attach_smooth_scroll


def build_smooth_scroll_demo_widget() -> QWidget:
    """Creates a minimal widget for manual smooth-scroll verification."""
    root = QWidget()
    root.setWindowTitle("Smooth Scroll Demo")
    layout = QVBoxLayout(root)

    title = QLabel("Smooth Scroll Demo")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)

    list_widget = QListWidget()
    list_widget.setAlternatingRowColors(True)
    for index in range(1, 301):
        list_widget.addItem(QListWidgetItem(f"Demo row {index:03d}"))
    layout.addWidget(list_widget, 1)

    root._smooth_scroll = attach_smooth_scroll(
        list_widget,
        SmoothScrollConfig(
            frame_interval_ms=12,
            easing_factor=0.33,
            wheel_step_px=42,
            max_step_px=120,
        ),
    )
    return root
