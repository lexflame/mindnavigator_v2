"""OverlayEditDialog class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class OverlayEditDialog(QDialog):
    def __init__(self, overlay: MapOverlay, parent=None):
        super().__init__(parent)
        self.setObjectName("OverlayEditDialog")
        self.setWindowTitle("Редактирование геометрии")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._overlay = overlay
        self._selected_color = QColor(overlay.color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit(overlay.title)
        self.title_edit.setPlaceholderText("Название области или пути")

        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Область", "region")
        self.kind_combo.addItem("Путь", "path")
        kind_index = self.kind_combo.findData(overlay.kind)
        if kind_index >= 0:
            self.kind_combo.setCurrentIndex(kind_index)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(28, 28)
        self.color_preview.setObjectName("OverlayColorPreview")
        self.color_button = QToolButton()
        self.color_button.setText("Выбрать цвет…")
        self.color_button.clicked.connect(self._pick_color)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button, 1)
        self._refresh_color_preview()

        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.kind_combo)
        form.addRow("Цвет", color_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#OverlayEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#OverlayEditDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#OverlayEditDialog QLineEdit,
            QDialog#OverlayEditDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}
            QDialog#OverlayEditDialog QDialogButtonBox QPushButton,
            QDialog#OverlayEditDialog QToolButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }}
            QDialog#OverlayEditDialog QDialogButtonBox QPushButton:hover,
            QDialog#OverlayEditDialog QToolButton:hover {{
                background: #34363b;
            }}
            QLabel#OverlayColorPreview {{
                border: 1px solid #3a3b40;
                border-radius: 4px;
                background: #202127;
            }}
            """
        )

    def _pick_color(self) -> None:
        chosen = QColorDialog.getColor(self._selected_color, self, "Цвет геометрии")
        if not chosen.isValid():
            return
        self._selected_color = chosen
        self._refresh_color_preview()

    def _refresh_color_preview(self) -> None:
        self.color_preview.setStyleSheet(
            f"background: {self._selected_color.name()}; border: 1px solid #3a3b40; border-radius: 4px;"
        )

    def _on_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Проверка", "Название не может быть пустым.")
            return
        kind = self.kind_combo.currentData() or self._overlay.kind
        min_points = 3 if kind == "region" else 2
        if len(self._overlay.points) < min_points:
            QMessageBox.warning(self, "Проверка", "Недостаточно точек для выбранного типа.")
            return
        self.accept()

    def values(self) -> tuple[str, str, QColor]:
        return (
            self.title_edit.text().strip(),
            self.kind_combo.currentData() or self._overlay.kind,
            QColor(self._selected_color),
        )

__all__ = ["OverlayEditDialog"]
