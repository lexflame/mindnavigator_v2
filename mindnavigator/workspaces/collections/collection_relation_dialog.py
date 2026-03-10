"""CollectionRelationDialog class module for collections workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

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
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._source_item = source_item
        self._candidates_by_id: Dict[int, CollectionItemData] = {}
        self.target_combo = QComboBox()
        for item in candidates:
            label = f"{ENTITY_LABELS.get(item.entity_type, item.entity_type)} · {item.title}"
            self.target_combo.addItem(label, item.id)
            self._candidates_by_id[item.id] = item

        self.template_combo = QComboBox()
        for label, value in RELATION_TEMPLATE_CHOICES:
            self.template_combo.addItem(label, value)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.target_combo.currentIndexChanged.connect(self._sync_template_for_selection)

        self.kind_edit = QLineEdit("")
        self.kind_edit.setPlaceholderText("Произвольный тип связи")
        self.kind_edit.setEnabled(False)

        form.addRow("Связать с", self.target_combo)
        form.addRow("Шаблон связи", self.template_combo)
        form.addRow("Пользовательский тип", self.kind_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
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
        self._sync_template_for_selection()

    def _accept(self) -> None:
        if self.target_combo.currentData() is None:
            QMessageBox.warning(self, "Связи", "Выберите элемент для связи.")
            return
        self.accept()

    def values(self) -> dict:
        template_value = self.template_combo.currentData()
        if template_value == "__auto__":
            relation_kind = self._suggest_template_for_current_target() or "="
        elif template_value == "__custom__":
            relation_kind = self.kind_edit.text().strip() or "="
        else:
            relation_kind = template_value
        return {
            "target_id": self.target_combo.currentData(),
            "relation_kind": relation_kind,
        }

    def _suggest_template_for_current_target(self) -> str:
        target_id = self.target_combo.currentData()
        target_item = self._candidates_by_id.get(target_id)
        if target_item is None:
            return "="
        key = frozenset((self._source_item.entity_type, target_item.entity_type))
        return RELATION_TYPE_MAP.get(key, "=")

    def _sync_template_for_selection(self) -> None:
        if self.template_combo.currentData() == "__auto__":
            self.kind_edit.setText(self._suggest_template_for_current_target())

    def _on_template_changed(self) -> None:
        value = self.template_combo.currentData()
        if value == "__custom__":
            self.kind_edit.setEnabled(True)
            if not self.kind_edit.text().strip():
                self.kind_edit.setText("=")
        elif value == "__auto__":
            self.kind_edit.setEnabled(False)
            self.kind_edit.setText(self._suggest_template_for_current_target())
        else:
            self.kind_edit.setEnabled(False)
            self.kind_edit.setText(value)

__all__ = ["CollectionRelationDialog"]
