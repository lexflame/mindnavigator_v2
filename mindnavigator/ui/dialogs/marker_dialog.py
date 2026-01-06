
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QDoubleSpinBox, QComboBox, QDialogButtonBox
)

from .multi_select_list import MultiSelectList


class MarkerDialog(QDialog):
    def __init__(self, parent=None, *, initial=None, tasks_rows=None, projects_rows=None,
                 selected_task_ids=None, selected_project_ids=None):
        super().__init__(parent)
        self.setWindowTitle("Метка")

        self.title = QLineEdit()
        self.x = QDoubleSpinBox(); self.x.setRange(-1e9, 1e9); self.x.setDecimals(3)
        self.y = QDoubleSpinBox(); self.y.setRange(-1e9, 1e9); self.y.setDecimals(3)
        self.color = QComboBox(); self.color.addItems(["", "#50c878", "#ff4d4d", "#3fa9f5", "#f5d547"])
        self.icon = QComboBox(); self.icon.addItems(["", "dot", "flag", "star", "poi"])
        self.note = QTextEdit()

        self.projects = MultiSelectList()
        self.tasks = MultiSelectList()

        if initial:
            self.title.setText(initial.get("title", ""))
            self.x.setValue(float(initial.get("x", 0)))
            self.y.setValue(float(initial.get("y", 0)))
            if initial.get("color"):
                i = self.color.findText(initial["color"])
                if i >= 0:
                    self.color.setCurrentIndex(i)
            if initial.get("icon"):
                i = self.icon.findText(initial["icon"])
                if i >= 0:
                    self.icon.setCurrentIndex(i)
            self.note.setPlainText(initial.get("note", ""))

        if projects_rows is not None:
            self.projects.set_items(projects_rows, id_key="id", title_key="title", selected_ids=selected_project_ids)
        if tasks_rows is not None:
            self.tasks.set_items(tasks_rows, id_key="id", title_key="title", selected_ids=selected_task_ids)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Название"))
        lay.addWidget(self.title)

        row = QHBoxLayout()
        row.addWidget(QLabel("X")); row.addWidget(self.x)
        row.addWidget(QLabel("Y")); row.addWidget(self.y)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Color")); row2.addWidget(self.color, 1)
        row2.addWidget(QLabel("Icon")); row2.addWidget(self.icon, 1)
        lay.addLayout(row2)

        lay.addWidget(QLabel("Заметка"))
        lay.addWidget(self.note)

        lay.addWidget(QLabel("Проекты (привязки)"))
        lay.addWidget(self.projects, 1)

        lay.addWidget(QLabel("Задачи (привязки)"))
        lay.addWidget(self.tasks, 1)

        lay.addWidget(btns)

    def get_data(self):
        return {
            "title": self.title.text().strip(),
            "x": float(self.x.value()),
            "y": float(self.y.value()),
            "color": self.color.currentText() or None,
            "icon": self.icon.currentText() or None,
            "note": self.note.toPlainText().strip(),
            "project_ids": self.projects.selected_ids(),
            "task_ids": self.tasks.selected_ids(),
        }
