"""Typed create/edit dialog surfaces for Dossier items."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403


class _DossierEditorDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        initial: DossierData | None = None,
        dialog_title: str,
        accept_text: str,
        seed_kind: str = "book",
        seed_title: str = "",
    ) -> None:
        super().__init__(parent)
        self._theme_mode = resolve_theme_mode(parent)
        self._initial = initial
        self._accept_text = accept_text
        self._metadata_widgets: dict[str, tuple[str, QWidget]] = {}
        self._metadata_values_by_kind: dict[str, dict[str, object]] = {
            kind: {} for kind in DossierData.SUPPORTED_KINDS
        }
        if initial is not None:
            self._metadata_values_by_kind[initial.kind] = dict(initial.metadata)
        self._current_metadata_kind = initial.kind if initial is not None else seed_kind
        self._build_ui(dialog_title)
        self._fill_initial(initial=initial, seed_kind=seed_kind, seed_title=seed_title)

    def _build_ui(self, dialog_title: str) -> None:
        self.setWindowTitle(dialog_title)
        self.setObjectName("DossierEditorDialog")
        self.setMinimumWidth(720)
        self.setMinimumHeight(760)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(dialog_title)
        title_label.setObjectName("DialogTitle")
        root_layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setObjectName("DossierEditorScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("DossierEditorContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        common_card = QFrame()
        common_card.setObjectName("DossierEditorCard")
        common_layout = QVBoxLayout(common_card)
        common_layout.setContentsMargins(14, 12, 14, 12)
        common_layout.setSpacing(10)

        common_title = QLabel("Общие поля")
        common_title.setObjectName("DossierEditorSectionTitle")
        common_layout.addWidget(common_title)

        common_form = QFormLayout()
        common_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        common_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        common_form.setHorizontalSpacing(14)
        common_form.setVerticalSpacing(8)

        self.kind_combo = QComboBox()
        for label, value in DOSSIER_KIND_OPTIONS[1:]:
            self.kind_combo.addItem(label, value)
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)

        self.status_combo = QComboBox()
        for label, value in DOSSIER_STATUS_OPTIONS[1:]:
            self.status_combo.addItem(label, value)

        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 10)
        self.rating_spin.setSpecialValueText("Без оценки")

        self.title_edit = QLineEdit()
        self.summary_edit = QLineEdit()
        self.description_edit = QPlainTextEdit()
        self.description_edit.setMinimumHeight(140)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Через запятую")
        self.source_edit = QLineEdit()
        self.cover_image_edit = QLineEdit()

        common_form.addRow("Вид", self.kind_combo)
        common_form.addRow("Название", self.title_edit)
        common_form.addRow("Кратко", self.summary_edit)
        common_form.addRow("Описание", self.description_edit)
        common_form.addRow("Теги", self.tags_edit)
        common_form.addRow("Статус", self.status_combo)
        common_form.addRow("Рейтинг", self.rating_spin)
        common_form.addRow("Источник", self.source_edit)
        common_form.addRow("Обложка / изображение", self.cover_image_edit)
        common_layout.addLayout(common_form)
        content_layout.addWidget(common_card)

        metadata_card = QFrame()
        metadata_card.setObjectName("DossierEditorCard")
        metadata_layout = QVBoxLayout(metadata_card)
        metadata_layout.setContentsMargins(14, 12, 14, 12)
        metadata_layout.setSpacing(10)

        self.metadata_title = QLabel("Типовые поля")
        self.metadata_title.setObjectName("DossierEditorSectionTitle")
        metadata_layout.addWidget(self.metadata_title)

        self.metadata_host = QWidget()
        self.metadata_host_layout = QVBoxLayout(self.metadata_host)
        self.metadata_host_layout.setContentsMargins(0, 0, 0, 0)
        self.metadata_host_layout.setSpacing(0)
        metadata_layout.addWidget(self.metadata_host)
        content_layout.addWidget(metadata_card)
        content_layout.addStretch(1)

        scroll.setWidget(content)

        buttons = QDialogButtonBox(self)
        save_button = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        save_button.setText(self._accept_text)
        save_button.clicked.connect(self._on_accept)
        cancel_button.clicked.connect(self.reject)
        root_layout.addWidget(buttons)

        palette = get_theme_palette(self._theme_mode)
        scrollbar_qss = build_scrollbar_stylesheet(
            get_scrollbar_tokens(self._theme_mode),
            scope="QDialog#DossierEditorDialog",
        )
        self.setStyleSheet(
            f"""
            QDialog#DossierEditorDialog {{
                background: {palette.window_bg};
                color: {palette.text};
            }}
            QDialog#DossierEditorDialog QLabel {{
                color: {palette.text};
            }}
            QDialog#DossierEditorDialog QLabel#DialogTitle {{
                color: {palette.selection_text};
                font-size: 19px;
                font-weight: 700;
            }}
            QDialog#DossierEditorDialog QLabel#DossierEditorSectionTitle {{
                color: {palette.selection_text};
                font-weight: 600;
            }}
            QDialog#DossierEditorDialog QScrollArea#DossierEditorScroll,
            QDialog#DossierEditorDialog QWidget#DossierEditorContent {{
                background: transparent;
                border: none;
            }}
            QFrame#DossierEditorCard {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QDialog#DossierEditorDialog QLineEdit,
            QDialog#DossierEditorDialog QPlainTextEdit,
            QDialog#DossierEditorDialog QComboBox,
            QDialog#DossierEditorDialog QSpinBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QDialog#DossierEditorDialog QLineEdit:focus,
            QDialog#DossierEditorDialog QPlainTextEdit:focus,
            QDialog#DossierEditorDialog QComboBox:focus,
            QDialog#DossierEditorDialog QSpinBox:focus {{
                border: 1px solid {palette.accent};
            }}
            QDialog#DossierEditorDialog QComboBox QAbstractItemView {{
                background: {palette.elevated_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                selection-background-color: {palette.selection_bg};
                selection-color: {palette.selection_text};
                outline: none;
            }}
            QDialog#DossierEditorDialog QDialogButtonBox QPushButton {{
                background: {palette.panel_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QDialog#DossierEditorDialog QDialogButtonBox QPushButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            {scrollbar_qss}
            """
        )

    def _fill_initial(
        self,
        *,
        initial: DossierData | None,
        seed_kind: str,
        seed_title: str,
    ) -> None:
        if initial is not None:
            self._set_combo_value(self.kind_combo, initial.kind)
            self._set_combo_value(self.status_combo, initial.status)
            self.title_edit.setText(initial.title)
            self.summary_edit.setText(initial.summary)
            self.description_edit.setPlainText(initial.description)
            self.tags_edit.setText(", ".join(initial.tags))
            self.rating_spin.setValue(initial.rating or 0)
            self.source_edit.setText(initial.source)
            self.cover_image_edit.setText(initial.cover_image)
        else:
            self._set_combo_value(self.kind_combo, seed_kind)
            self._set_combo_value(self.status_combo, "planned")
            self.title_edit.setText(seed_title)
        self._rebuild_metadata_form(self.kind_combo.currentData() or seed_kind)
        self.title_edit.setFocus()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def _snapshot_metadata_values(self) -> dict[str, object]:
        values: dict[str, object] = {}
        for field_name, (field_type, widget) in self._metadata_widgets.items():
            if field_type == "int" and isinstance(widget, QSpinBox):
                if widget.value() > 0:
                    values[field_name] = widget.value()
                continue
            if field_type == "list" and isinstance(widget, QLineEdit):
                parsed = parse_tag_list(widget.text())
                if parsed:
                    values[field_name] = parsed
                continue
            if field_name == "notable_works_summary" and isinstance(widget, QPlainTextEdit):
                text = widget.toPlainText().strip()
                if text:
                    values[field_name] = text
                continue
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if text:
                    values[field_name] = text
        return values

    def _on_kind_changed(self) -> None:
        next_kind = self.kind_combo.currentData()
        if not isinstance(next_kind, str):
            return
        if self._current_metadata_kind in self._metadata_values_by_kind:
            self._metadata_values_by_kind[self._current_metadata_kind] = self._snapshot_metadata_values()
        self._rebuild_metadata_form(next_kind)

    def _rebuild_metadata_form(self, kind: str) -> None:
        while self.metadata_host_layout.count():
            item = self.metadata_host_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._metadata_widgets = {}
        self._current_metadata_kind = kind

        form_host = QWidget()
        form_layout = QFormLayout(form_host)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(8)

        stored_values = self._metadata_values_by_kind.get(kind, {})
        field_definitions = DossierData.METADATA_FIELDS[kind]
        self.metadata_title.setText(f"Типовые поля: {dossier_kind_label(kind)}")

        for field_name, field_type in field_definitions.items():
            label_text = DOSSIER_METADATA_LABELS.get(field_name, field_name.replace("_", " ").title())
            if field_type == "int":
                widget = QSpinBox()
                widget.setRange(0, 100000)
                widget.setSpecialValueText("—")
                widget.setValue(int(stored_values.get(field_name) or 0))
            elif field_type == "list":
                widget = QLineEdit()
                current_items = stored_values.get(field_name)
                if isinstance(current_items, list):
                    widget.setText(", ".join(str(item) for item in current_items))
                widget.setPlaceholderText("Через запятую")
            elif field_name == "notable_works_summary":
                widget = QPlainTextEdit()
                widget.setMinimumHeight(90)
                widget.setPlainText(str(stored_values.get(field_name) or ""))
            else:
                widget = QLineEdit()
                widget.setText(str(stored_values.get(field_name) or ""))
            self._metadata_widgets[field_name] = (field_type, widget)
            form_layout.addRow(label_text, widget)

        self.metadata_host_layout.addWidget(form_host)

    def values(self) -> dict[str, object]:
        self._metadata_values_by_kind[self._current_metadata_kind] = self._snapshot_metadata_values()
        kind = str(self.kind_combo.currentData() or "book")
        rating_value = self.rating_spin.value()
        return {
            "kind": kind,
            "title": self.title_edit.text().strip(),
            "summary": self.summary_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "tags": parse_tag_list(self.tags_edit.text()),
            "status": str(self.status_combo.currentData() or "planned"),
            "rating": rating_value if rating_value > 0 else None,
            "source": self.source_edit.text().strip(),
            "cover_image": self.cover_image_edit.text().strip(),
            "metadata": dict(self._metadata_values_by_kind.get(kind, {})),
        }

    def _on_accept(self) -> None:
        values = self.values()
        if not str(values["title"]).strip():
            QMessageBox.warning(self, "Проверка", "Введите название досье.")
            return
        try:
            DossierData.normalize_kind(str(values["kind"]))
            DossierData.normalize_status(str(values["status"]))
            DossierData.normalize_rating(values["rating"])
            DossierData.normalize_metadata(str(values["kind"]), values["metadata"])
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()


class DossierCreateDialog(_DossierEditorDialog):
    def __init__(
        self,
        *,
        parent: QWidget | None = None,
        seed_kind: str = "book",
        seed_title: str = "",
    ) -> None:
        super().__init__(
            parent=parent,
            initial=None,
            dialog_title="Создание досье",
            accept_text="Создать",
            seed_kind=seed_kind,
            seed_title=seed_title,
        )


class DossierEditDialog(_DossierEditorDialog):
    def __init__(self, dossier: DossierData, parent: QWidget | None = None) -> None:
        super().__init__(
            parent=parent,
            initial=dossier,
            dialog_title="Редактирование досье",
            accept_text="Сохранить",
            seed_kind=dossier.kind,
            seed_title=dossier.title,
        )


__all__ = ["DossierCreateDialog", "DossierEditDialog"]
