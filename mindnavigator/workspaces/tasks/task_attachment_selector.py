"""Shared task attachment selector helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QVBoxLayout

from mindnavigator.ui.filterable_combobox import FilterableComboBox
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


@dataclass(frozen=True)
class TaskAttachmentSources:
    tasks_by_id: dict[int, object]
    notes_by_id: dict[int, object]
    ideas_by_id: dict[int, object]
    objects_by_id: dict[int, object]
    maps_by_id: dict[int, object]
    markers_by_id: dict[int, object]
    cloud_files_by_id: dict[int, object]


def safe_fetch(db, method_name: str, *args, **kwargs) -> list:
    fetch_method = getattr(db, method_name, None)
    if not callable(fetch_method):
        return []
    return list(fetch_method(*args, **kwargs) or [])


def load_task_attachment_sources(db, *, safe: bool = False) -> TaskAttachmentSources:
    fetch = (lambda name, *args, **kwargs: safe_fetch(db, name, *args, **kwargs)) if safe else (
        lambda name, *args, **kwargs: list(getattr(db, name)(*args, **kwargs) or [])
    )
    tasks = fetch("fetch_tasks")
    notes = fetch("fetch_notes")
    ideas_active = fetch("fetch_ideas", archived=False)
    active_ids = {idea.id for idea in ideas_active}
    ideas_archived = [idea for idea in fetch("fetch_ideas", archived=True) if idea.id not in active_ids]
    ideas = ideas_active + ideas_archived
    objects = fetch("fetch_objects")
    maps = fetch("fetch_maps")
    markers = fetch("fetch_map_markers")
    cloud_files = fetch("fetch_cloud_files")
    return TaskAttachmentSources(
        tasks_by_id={item.id: item for item in tasks},
        notes_by_id={item.id: item for item in notes},
        ideas_by_id={item.id: item for item in ideas},
        objects_by_id={item.id: item for item in objects},
        maps_by_id={item.id: item for item in maps},
        markers_by_id={item.id: item for item in markers},
        cloud_files_by_id={item.id: item for item in cloud_files},
    )


def cloud_file_link_text(file_item) -> str:
    description = (file_item.description or "").strip()
    if description:
        try:
            payload = json.loads(description)
        except json.JSONDecodeError:
            return description
        if isinstance(payload, dict):
            text = (payload.get("text") or "").strip()
            if text:
                return text
    return file_item.name


def attachment_candidate_items(
    sources: TaskAttachmentSources,
    kind: str,
    *,
    current_task_id: int,
) -> list[tuple[str, int]]:
    if kind == "task":
        tasks = [task for task in sources.tasks_by_id.values() if task.id != current_task_id]
        return [
            (f"{task.title} · {task.project_title}" if task.project_title else task.title, task.id)
            for task in sorted(tasks, key=lambda item: (item.title.lower(), item.id))
        ]
    if kind == "note":
        return [
            (f"{note.title} · {note.project}" if note.project else note.title, note.id)
            for note in sorted(sources.notes_by_id.values(), key=lambda item: item.title.lower())
        ]
    if kind == "idea":
        return [
            (f"{idea.title} · {idea.project_title}" if idea.project_title else idea.title, idea.id)
            for idea in sorted(sources.ideas_by_id.values(), key=lambda item: item.title.lower())
        ]
    if kind == "object":
        return [
            (f"{obj.title} · {obj.catalog}" if obj.catalog else obj.title, obj.id)
            for obj in sorted(sources.objects_by_id.values(), key=lambda item: item.title.lower())
        ]
    if kind == "map":
        return [
            (f"{map_item.title} · {map_item.project}" if map_item.project else map_item.title, map_item.id)
            for map_item in sorted(sources.maps_by_id.values(), key=lambda item: item.title.lower())
        ]
    if kind == "marker":
        markers = sorted(sources.markers_by_id.values(), key=lambda item: item.name.lower())
        rows: list[tuple[str, int]] = []
        for marker in markers:
            map_item = sources.maps_by_id.get(marker.map_id)
            map_title = map_item.title if map_item is not None else ""
            rows.append((f"{marker.name} · {map_title}" if map_title else marker.name, marker.id))
        return rows
    if kind in {"file", "image"}:
        files = [
            file_item
            for file_item in sources.cloud_files_by_id.values()
            if file_item.is_image == (kind == "image")
        ]
        return [
            (cloud_file_link_text(file_item), file_item.id)
            for file_item in sorted(files, key=lambda item: item.name.lower())
        ]
    return []


def find_cloud_file_id_by_rel_path(
    sources: TaskAttachmentSources,
    rel_path: str,
    *,
    image: bool = False,
) -> Optional[int]:
    normalized = rel_path.strip().strip("/")
    return next(
        (
            file_item.id
            for file_item in sources.cloud_files_by_id.values()
            if (file_item.rel_path or "").strip().strip("/") == normalized
            and file_item.is_image == image
        ),
        None,
    )


def create_task_attachment_dialog(
    parent,
    sources: TaskAttachmentSources,
    *,
    current_task_id: int,
    kind: str | None = None,
    file_picker_factory: Callable | None = None,
) -> tuple[QDialog, QComboBox, FilterableComboBox]:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Добавить связь")
    dialog.setObjectName("TaskAttachmentDialog")
    dialog.setFixedSize(550, 200)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
    form.setHorizontalSpacing(10)
    form.setVerticalSpacing(8)

    kind_combo = QComboBox(dialog)
    kind_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
    for label, key in (
        ("Задача", "task"),
        ("Заметка", "note"),
        ("Идея", "idea"),
        ("Объект", "object"),
        ("Карта", "map"),
        ("Метка карты", "marker"),
        ("Файл", "file"),
        ("Изображение", "image"),
    ):
        if kind is None or key == kind:
            kind_combo.addItem(label, key)

    item_combo = FilterableComboBox(dialog)
    item_combo.setMinimumContentsLength(24)
    item_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    item_view = item_combo.view()
    if item_view is not None:
        item_view.setTextElideMode(Qt.TextElideMode.ElideMiddle)

    file_picker_open = {"active": False}

    def fill_items(selected_kind: str) -> None:
        item_combo.clear()
        for label, ref_id in attachment_candidate_items(sources, selected_kind, current_task_id=current_task_id):
            item_combo.addItem(label, ref_id)
        if item_combo.count() == 0:
            item_combo.addItem("— нет доступных —", None)
        item_combo.clear_filter()
        item_combo.setCurrentIndex(0 if item_combo.count() else -1)

    def select_file_from_picker() -> None:
        if file_picker_factory is None or file_picker_open["active"]:
            return
        file_picker_open["active"] = True
        try:
            picker = file_picker_factory(parent)
            if int(picker.exec()) != int(QDialog.DialogCode.Accepted):
                return
            rel_path = picker.selected_rel_path()
        finally:
            file_picker_open["active"] = False
        if not rel_path:
            return
        selected_file_id = find_cloud_file_id_by_rel_path(sources, rel_path, image=False)
        if selected_file_id is None:
            QMessageBox.warning(parent, "Связи", "Файл не найден в базе.")
            return
        selected_index = item_combo.findData(selected_file_id)
        if selected_index >= 0:
            item_combo.setCurrentIndex(selected_index)

    def on_kind_changed(_idx: int) -> None:
        selected_kind = str(kind_combo.currentData() or "")
        fill_items(selected_kind)
        if selected_kind == "file":
            QTimer.singleShot(0, select_file_from_picker)

    kind_combo.currentIndexChanged.connect(on_kind_changed)
    fill_items(str(kind_combo.currentData() or ""))

    form.addRow("Тип", kind_combo)
    form.addRow("Элемент", item_combo)
    layout.addLayout(form)

    buttons = QDialogButtonBox(dialog)
    buttons.addButton(QDialogButtonBox.StandardButton.Ok)
    buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.setStyleSheet(f"""
        QDialog#TaskAttachmentDialog {{
            {MATH_PHYS_BACKGROUND}
        }}
        QDialog#TaskAttachmentDialog QLabel {{
            color: #cfcfcf;
        }}
        QDialog#TaskAttachmentDialog QComboBox {{
            background: #202127;
            color: #e6e6e6;
            border: 1px solid #2a2b2f;
            padding: 4px 8px;
            border-radius: 6px;
            min-height: 28px;
        }}
        QDialog#TaskAttachmentDialog QDialogButtonBox QPushButton {{
            background: #2a2b2f;
            color: #e6e6e6;
            border: 1px solid #3a3b40;
            padding: 4px 10px;
            min-height: 28px;
            border-radius: 6px;
        }}
    """)
    return dialog, kind_combo, item_combo


__all__ = [
    "TaskAttachmentSources",
    "attachment_candidate_items",
    "cloud_file_link_text",
    "create_task_attachment_dialog",
    "find_cloud_file_id_by_rel_path",
    "load_task_attachment_sources",
    "safe_fetch",
]
