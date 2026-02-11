"""Workspace for thematic collections and cross-links between items."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.storage import CollectionItemData, CollectionRelationData, get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND

ENTITY_LABELS = {
    "building": "Здание",
    "city": "Город",
    "film": "Фильм",
    "game": "Игра",
    "character": "Персонаж",
    "other": "Другое",
}

ENTITY_CHOICES = [
    ("Здание", "building"),
    ("Город", "city"),
    ("Фильм", "film"),
    ("Игра", "game"),
    ("Персонаж", "character"),
    ("Другое", "other"),
]


class CollectionItemEditDialog(QDialog):
    def __init__(self, item: Optional[CollectionItemData] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("CollectionItemEditDialog")
        self.setWindowTitle("Создание элемента коллекции" if item is None else "Редактирование элемента коллекции")
        self.setMinimumSize(620, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Новый элемент коллекции" if item is None else "Редактирование элемента коллекции")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit(item.title if item else "")
        self.title_edit.setPlaceholderText("Название")

        self.type_edit = QComboBox()
        for label, value in ENTITY_CHOICES:
            self.type_edit.addItem(label, value)
        if item is not None:
            idx = self.type_edit.findData(item.entity_type)
            if idx >= 0:
                self.type_edit.setCurrentIndex(idx)

        self.topic_edit = QLineEdit(item.topic if item else "")
        self.topic_edit.setPlaceholderText("Тема (например: sci-fi, архитектура, индустриальный урбанизм)")

        self.image_url_edit = QLineEdit(item.image_url if item else "")
        self.image_url_edit.setPlaceholderText("Ссылка на изображение")

        self.source_url_edit = QLineEdit(item.source_url if item else "")
        self.source_url_edit.setPlaceholderText("Ссылка на источник")

        self.description_edit = QPlainTextEdit(item.description if item else "")
        self.description_edit.setPlaceholderText("Описание / заметка")
        self.description_edit.setMinimumHeight(130)

        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.type_edit)
        form.addRow("Тема", self.topic_edit)
        form.addRow("Изображение URL", self.image_url_edit)
        form.addRow("Источник URL", self.source_url_edit)
        form.addRow("Описание", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText("Создать" if item is None else "Сохранить")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionItemEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionItemEditDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionItemEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#CollectionItemEditDialog QLineEdit,
            QDialog#CollectionItemEditDialog QPlainTextEdit,
            QDialog#CollectionItemEditDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionItemEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название элемента.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "title": self.title_edit.text().strip(),
            "entity_type": self.type_edit.currentData(),
            "topic": self.topic_edit.text().strip(),
            "image_url": self.image_url_edit.text().strip(),
            "source_url": self.source_url_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
        }


class CollectionRelationDialog(QDialog):
    def __init__(self, source_item: CollectionItemData, candidates: List[CollectionItemData], parent=None):
        super().__init__(parent)
        self.setObjectName("CollectionRelationDialog")
        self.setWindowTitle("Создать связь")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Связать: {source_item.title}")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.target_combo = QComboBox()
        for item in candidates:
            label = f"{ENTITY_LABELS.get(item.entity_type, item.entity_type)} · {item.title}"
            self.target_combo.addItem(label, item.id)

        self.kind_edit = QLineEdit("=")
        self.kind_edit.setPlaceholderText("Тип связи, например: =, по мотивам, вдохновлено")

        form.addRow("Связать с", self.target_combo)
        form.addRow("Тип связи", self.kind_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText("Создать связь")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionRelationDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionRelationDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionRelationDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }}
            QDialog#CollectionRelationDialog QLineEdit,
            QDialog#CollectionRelationDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionRelationDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def _accept(self) -> None:
        if self.target_combo.currentData() is None:
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "target_id": self.target_combo.currentData(),
            "relation_kind": self.kind_edit.text().strip() or "=",
        }


class CollectionsWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = get_database()
        self._items: List[CollectionItemData] = []
        self._items_by_id: Dict[int, CollectionItemData] = {}
        self._relations: List[CollectionRelationData] = []
        self._current_item_id: Optional[int] = None
        self._build_ui()
        self.refresh_collections()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Коллекции")
        title.setObjectName("CollectionsTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по коллекциям...")
        self.search_edit.textChanged.connect(self.refresh_collections)

        self.topic_filter = QComboBox()
        self.topic_filter.currentIndexChanged.connect(self.refresh_collections)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Все типы", "")
        for label, value in ENTITY_CHOICES:
            self.type_filter.addItem(label, value)
        self.type_filter.currentIndexChanged.connect(self.refresh_collections)

        self.add_button = QToolButton()
        self.add_button.setText("Добавить")
        self.add_button.clicked.connect(self._add_item)

        header.addWidget(self.search_edit)
        header.addWidget(self.topic_filter)
        header.addWidget(self.type_filter)
        header.addWidget(self.add_button)
        layout.addLayout(header)

        splitter = QSplitter()

        left = QFrame()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        self.items_list = QListWidget()
        self.items_list.currentItemChanged.connect(self._on_item_selected)
        left_layout.addWidget(self.items_list, 1)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        self.details_title = QLabel("Выберите элемент")
        self.details_title.setObjectName("CollectionsDetailsTitle")
        self.details_type = QLabel("")
        self.details_topic = QLabel("")
        self.details_links = QLabel("")
        self.details_links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.details_links.setOpenExternalLinks(True)
        self.details_description = QLabel("")
        self.details_description.setWordWrap(True)

        actions = QHBoxLayout()
        self.edit_button = QToolButton()
        self.edit_button.setText("Редактировать")
        self.edit_button.clicked.connect(self._edit_current_item)
        self.delete_button = QToolButton()
        self.delete_button.setText("Удалить")
        self.delete_button.clicked.connect(self._delete_current_item)
        self.link_button = QToolButton()
        self.link_button.setText("Создать связь")
        self.link_button.clicked.connect(self._add_relation)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.link_button)
        actions.addStretch(1)
        actions.addWidget(self.delete_button)

        rel_title = QLabel("Перекрестные связи")
        rel_title.setObjectName("CollectionsRelationsTitle")
        self.relations_list = QListWidget()
        self.remove_relation_button = QToolButton()
        self.remove_relation_button.setText("Удалить выбранную связь")
        self.remove_relation_button.clicked.connect(self._remove_relation)

        right_layout.addWidget(self.details_title)
        right_layout.addWidget(self.details_type)
        right_layout.addWidget(self.details_topic)
        right_layout.addWidget(self.details_links)
        right_layout.addWidget(self.details_description)
        right_layout.addLayout(actions)
        right_layout.addWidget(rel_title)
        right_layout.addWidget(self.relations_list, 1)
        right_layout.addWidget(self.remove_relation_button, 0, Qt.AlignRight)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        self._set_action_state(False)
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#CollectionsTitle {
                color: #e6e6e6;
                font-size: 20px;
                font-weight: 600;
            }
            QListWidget {
                background: #14171c;
                border: 1px solid #2f333b;
                border-radius: 10px;
                color: #e6e6e6;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #21242b;
            }
            QListWidget::item:selected {
                background: #2d3440;
            }
            QLineEdit, QComboBox {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
                min-height: 26px;
            }
            QToolButton {
                background: #232831;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #e6e6e6;
            }
            QLabel#CollectionsDetailsTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 600;
            }
            QLabel#CollectionsRelationsTitle {
                color: #d8d8d8;
                font-size: 13px;
                font-weight: 600;
            }
            """
        )

    def _set_action_state(self, has_selection: bool) -> None:
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.link_button.setEnabled(has_selection)
        self.remove_relation_button.setEnabled(has_selection)
        if not has_selection:
            self.details_title.setText("Выберите элемент")
            self.details_type.setText("")
            self.details_topic.setText("")
            self.details_links.setText("")
            self.details_description.setText("")
            self.relations_list.clear()

    def refresh_collections(self) -> None:
        selected_id = self._current_item_id
        topics = self._db.fetch_collection_topics()
        current_topic = self.topic_filter.currentData() if self.topic_filter.count() else ""
        self.topic_filter.blockSignals(True)
        self.topic_filter.clear()
        self.topic_filter.addItem("Все темы", "")
        for topic in topics:
            self.topic_filter.addItem(topic, topic)
        idx = self.topic_filter.findData(current_topic)
        if idx >= 0:
            self.topic_filter.setCurrentIndex(idx)
        self.topic_filter.blockSignals(False)

        self._items = self._db.fetch_collection_items(
            search_text=self.search_edit.text(),
            topic=self.topic_filter.currentData() or None,
            entity_type=self.type_filter.currentData() or None,
        )
        self._items_by_id = {item.id: item for item in self._items}

        self.items_list.blockSignals(True)
        self.items_list.clear()
        for item in self._items:
            label = f"{ENTITY_LABELS.get(item.entity_type, item.entity_type)} · {item.title}"
            if item.topic:
                label = f"{label}\n#{item.topic}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item.id)
            self.items_list.addItem(list_item)
        self.items_list.blockSignals(False)

        if not self._items:
            self._current_item_id = None
            self._set_action_state(False)
            return

        select_row = 0
        if selected_id is not None:
            for row in range(self.items_list.count()):
                if self.items_list.item(row).data(Qt.UserRole) == selected_id:
                    select_row = row
                    break
        self.items_list.setCurrentRow(select_row)
        self._on_item_selected(self.items_list.currentItem(), None)

    def _on_item_selected(self, current: Optional[QListWidgetItem], _previous) -> None:
        if current is None:
            self._current_item_id = None
            self._set_action_state(False)
            return
        item_id = current.data(Qt.UserRole)
        item = self._items_by_id.get(item_id)
        if item is None:
            self._set_action_state(False)
            return

        self._current_item_id = item.id
        self.details_title.setText(item.title)
        self.details_type.setText(f"Тип: {ENTITY_LABELS.get(item.entity_type, item.entity_type)}")
        self.details_topic.setText(f"Тема: {item.topic or '—'}")
        links: List[str] = []
        if item.source_url:
            links.append(f"<a href='{item.source_url}'>Источник</a>")
        if item.image_url:
            links.append(f"<a href='{item.image_url}'>Изображение</a>")
        self.details_links.setText(" · ".join(links) if links else "Ссылки: —")
        self.details_description.setText(item.description or "Описание не задано.")

        self._relations = self._db.fetch_collection_relations(item.id)
        self.relations_list.clear()
        all_items = {it.id: it for it in self._db.fetch_collection_items()}
        for rel in self._relations:
            other_id = rel.right_item_id if rel.left_item_id == item.id else rel.left_item_id
            other = all_items.get(other_id)
            if other is None:
                continue
            text = f"{item.title} {rel.relation_kind} {other.title}"
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, rel.id)
            self.relations_list.addItem(row)
        self._set_action_state(True)

    def _add_item(self) -> None:
        dialog = CollectionItemEditDialog(parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        try:
            self._db.create_collection_item(**dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _current_item(self) -> Optional[CollectionItemData]:
        if self._current_item_id is None:
            return None
        return next((item for item in self._items if item.id == self._current_item_id), None)

    def _edit_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = CollectionItemEditDialog(item=item, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        try:
            self._db.update_collection_item(item.id, **dialog.values())
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self.refresh_collections()

    def _delete_current_item(self) -> None:
        item = self._current_item()
        if item is None:
            return
        dialog = ConfirmDialog(
            "Удалить элемент",
            f"Удалить элемент «{item.title}» и все его связи?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if show_dialog_standard(dialog, self) != QDialog.Accepted:
            return
        self._db.delete_collection_item(item.id)
        self.refresh_collections()

    def _add_relation(self) -> None:
        item = self._current_item()
        if item is None:
            return
        candidates = [it for it in self._db.fetch_collection_items() if it.id != item.id]
        if not candidates:
            QMessageBox.information(self, "Связи", "Нет доступных элементов для связывания.")
            return
        dialog = CollectionRelationDialog(item, candidates, parent=self)
        if exec_with_overlay(dialog, self) != QDialog.Accepted:
            return
        values = dialog.values()
        try:
            self._db.create_collection_relation(item.id, int(values["target_id"]), values["relation_kind"])
        except ValueError as exc:
            QMessageBox.warning(self, "Связи", str(exc))
            return
        self.refresh_collections()

    def _remove_relation(self) -> None:
        if self._current_item_id is None:
            return
        current = self.relations_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Связи", "Выберите связь для удаления.")
            return
        relation_id = current.data(Qt.UserRole)
        self._db.delete_collection_relation(int(relation_id))
        self.refresh_collections()
