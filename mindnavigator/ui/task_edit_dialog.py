from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QPushButton,
    QFormLayout,
)

from ..repositories.tasks_repo import TaskDTO
from ..repositories.projects_repo import ProjectDTO


class TaskEditDialog(QDialog):
    def __init__(self, parent=None, *, task: TaskDTO, projects: List[ProjectDTO]):
        super().__init__(parent)
        self.setWindowTitle("Редактирование задачи")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._task = task
        self._projects = projects

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.ed_title = QLineEdit(task.title)
        self.ed_title.setPlaceholderText("Название задачи")

        self.cmb_project = QComboBox()
        self.cmb_project.addItem("Без проекта", None)
        for p in projects:
            self.cmb_project.addItem(p.title, int(p.id))
        # select current
        cur_pid = task.project_id
        idx = self.cmb_project.findData(int(cur_pid) if cur_pid is not None else None)
        if idx >= 0:
            self.cmb_project.setCurrentIndex(idx)

        self.dt_day = QDateEdit()
        self.dt_day.setCalendarPopup(True)
        try:
            d = datetime.strptime(task.day, "%Y-%m-%d").date()
        except Exception:
            d = date.today()
        self.dt_day.setDate(d)

        self.ed_time = QLineEdit(task.time_text or "")
        self.ed_time.setPlaceholderText("HH:MM (необязательно)")

        self.cmb_priority = QComboBox()
        # значения в БД: Low|Medium|High + "Отложенная"
        self.cmb_priority.addItems(["Low", "Medium", "High", "Отложенная"])
        pr = task.priority or "Medium"
        i = self.cmb_priority.findText(pr)
        if i >= 0:
            self.cmb_priority.setCurrentIndex(i)
        else:
            self.cmb_priority.setCurrentText("Medium")

        self.chk_done = QCheckBox("Выполнено")
        self.chk_done.setChecked(bool(task.done))

        form.addRow("Название:", self.ed_title)
        form.addRow("Проект:", self.cmb_project)
        form.addRow("Дата:", self.dt_day)
        form.addRow("Время:", self.ed_time)
        form.addRow("Приоритет:", self.cmb_priority)
        form.addRow("", self.chk_done)

        root.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_ok = QPushButton("Сохранить")
        self.btn_ok.setDefault(True)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        root.addLayout(btns)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

    def get_data(self) -> dict:
        title = self.ed_title.text().strip()
        if not title:
            title = self._task.title

        pid = self.cmb_project.currentData()
        if pid is None:
            project_id = None
        else:
            project_id = int(pid)

        day = self.dt_day.date().toPython().isoformat()
        time_text = self.ed_time.text().strip()
        priority = self.cmb_priority.currentText().strip() or "Medium"
        done = bool(self.chk_done.isChecked())

        return {
            "title": title,
            "project_id": project_id,
            "day": day,
            "time_text": time_text,
            "priority": priority,
            "done": done,
        }
