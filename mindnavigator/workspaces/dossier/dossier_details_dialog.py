"""Read-only details dialog for a Dossier item."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403


class DossierDetailsDialog(QDialog):
    def __init__(self, dossier: DossierData, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._dossier = dossier
        self._theme_mode = resolve_theme_mode(parent)
        self.setWindowTitle("Карточка досье")
        self.setObjectName("DossierDetailsDialog")
        self.setMinimumWidth(760)
        self.setMinimumHeight(720)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_label = QLabel(self._dossier.title or "Без названия")
        title_label.setObjectName("DossierDetailsTitle")
        meta_label = QLabel(dossier_secondary_line(self._dossier))
        meta_label.setObjectName("DossierDetailsMeta")
        meta_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        header.addWidget(meta_label)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("DossierDetailsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("DossierDetailsContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_overview_card())
        content_layout.addWidget(self._build_description_card())
        content_layout.addWidget(self._build_metadata_card())
        content_layout.addWidget(self._build_notes_card())
        content_layout.addWidget(self._build_links_card())
        content_layout.addWidget(self._build_output_card())
        content_layout.addStretch(1)

        scroll.setWidget(content)

        buttons = QDialogButtonBox(self)
        edit_button = buttons.addButton("Изменить", QDialogButtonBox.ButtonRole.ActionRole)
        edit_button.clicked.connect(self._open_edit_dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        palette = get_theme_palette(self._theme_mode)
        scrollbar_qss = build_scrollbar_stylesheet(
            get_scrollbar_tokens(self._theme_mode),
            scope="QDialog#DossierDetailsDialog",
        )
        self.setStyleSheet(
            f"""
            QDialog#DossierDetailsDialog {{
                background: {palette.window_bg};
                color: {palette.text};
            }}
            QDialog#DossierDetailsDialog QLabel {{
                color: {palette.text};
            }}
            QLabel#DossierDetailsTitle {{
                color: {palette.selection_text};
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#DossierDetailsMeta {{
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 12px;
                padding: 6px 12px;
            }}
            QDialog#DossierDetailsDialog QScrollArea#DossierDetailsScroll,
            QDialog#DossierDetailsDialog QWidget#DossierDetailsContent {{
                background: transparent;
                border: none;
            }}
            QFrame#DossierDetailsCard {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}
            QLabel#DossierDetailsSectionTitle {{
                color: {palette.selection_text};
                font-weight: 600;
            }}
            QLabel#DossierDetailsCover {{
                background: {palette.panel_alt_bg};
                border: 1px dashed {palette.border_strong};
                border-radius: 10px;
                color: {palette.dim_text};
                padding: 8px;
            }}
            QDialog#DossierDetailsDialog QPlainTextEdit,
            QDialog#DossierDetailsDialog QListWidget {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 6px;
                padding: 6px 8px;
            }}
            QDialog#DossierDetailsDialog QListWidget::item:selected {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            QDialog#DossierDetailsDialog QDialogButtonBox QPushButton {{
                background: {palette.panel_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QDialog#DossierDetailsDialog QDialogButtonBox QPushButton:hover {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}
            {scrollbar_qss}
            """
        )

    def _open_edit_dialog(self) -> None:
        parent = self.parent()
        while parent is not None:
            edit_method = getattr(parent, "open_edit_selected_dossier", None)
            if callable(edit_method):
                self.accept()
                edit_method()
                return
            parent = parent.parent() if hasattr(parent, "parent") else None

    def _build_card(self, title_text: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("DossierDetailsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("DossierDetailsSectionTitle")
        card_layout.addWidget(title)
        return card, card_layout

    def _build_overview_card(self) -> QWidget:
        card, card_layout = self._build_card("Обзор")

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        cover_label = QLabel(dossier_kind_label(self._dossier.kind))
        cover_label.setObjectName("DossierDetailsCover")
        cover_label.setFixedSize(120, 162)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setWordWrap(True)
        pixmap = load_dossier_cover_pixmap(self._dossier.cover_image)
        if pixmap is not None:
            cover_label.setText("")
            cover_label.setPixmap(
                pixmap.scaled(
                    cover_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        top_layout.addWidget(cover_label)

        overview_text = QWidget()
        overview_text_layout = QVBoxLayout(overview_text)
        overview_text_layout.setContentsMargins(0, 0, 0, 0)
        overview_text_layout.setSpacing(8)

        summary = QLabel(self._dossier.summary or "Краткое описание пока не заполнено.")
        summary.setWordWrap(True)
        overview_text_layout.addWidget(summary)
        overview_text_layout.addWidget(QLabel(f"Теги: {dossier_tags_text(self._dossier.tags)}"))
        overview_text_layout.addWidget(QLabel(f"Источник: {self._dossier.source or 'Не указан'}"))
        overview_text_layout.addWidget(QLabel(f"Выход: {dossier_output_summary(self._db.fetch_dossier_links(self._dossier.id))}"))
        overview_text_layout.addStretch(1)
        top_layout.addWidget(overview_text, 1)

        card_layout.addWidget(top_row)
        return card

    def _build_description_card(self) -> QWidget:
        card, card_layout = self._build_card("Описание")

        description = QPlainTextEdit()
        description.setReadOnly(True)
        description.setPlainText(self._dossier.description or "")
        description.setMinimumHeight(160)
        card_layout.addWidget(description)
        return card

    def _build_metadata_card(self) -> QWidget:
        card, card_layout = self._build_card("Сведения")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        form.addRow("Вид", QLabel(dossier_kind_label(self._dossier.kind)))
        form.addRow("Статус", QLabel(dossier_status_label(self._dossier.status)))
        form.addRow("Рейтинг", QLabel(dossier_rating_label(self._dossier.rating)))
        form.addRow("Обложка", QLabel(self._dossier.cover_image or "—"))
        form.addRow("Создано", QLabel(self._dossier.created_at or "—"))
        form.addRow("Обновлено", QLabel(self._dossier.updated_at or "—"))

        for field_name in DossierData.METADATA_FIELDS[self._dossier.kind]:
            value = self._dossier.metadata.get(field_name)
            label_text = DOSSIER_METADATA_LABELS.get(field_name, field_name.replace("_", " ").title())
            form.addRow(label_text, QLabel(render_list_value(value) if value not in (None, "", []) else "—"))

        card_layout.addLayout(form)
        return card

    def _build_notes_card(self) -> QWidget:
        card, card_layout = self._build_card("Заметки")
        notes = QLabel(self._dossier.description or "Заметки пока не заполнены.")
        notes.setWordWrap(True)
        card_layout.addWidget(notes)
        return card

    def _build_links_card(self) -> QWidget:
        card, card_layout = self._build_card("Связи")

        links_list = QListWidget()
        links = self._db.fetch_dossier_links(self._dossier.id)
        if links:
            for link in links:
                label = self._db.describe_dossier_link_target(link.entity_kind, link.entity_id)
                links_list.addItem(QListWidgetItem(f"{DOSSIER_LINK_KIND_LABELS.get(link.entity_kind, link.entity_kind.title())}: {label}"))
        else:
            placeholder = QListWidgetItem(
                "Связей пока нет\nСвяжите досье с задачей, идеей, картой, объектом или персонажем."
            )
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            links_list.addItem(placeholder)
        card_layout.addWidget(links_list)
        return card

    def _build_output_card(self) -> QWidget:
        card, card_layout = self._build_card("Вывод")
        links = self._db.fetch_dossier_links(self._dossier.id)

        card_layout.addWidget(QLabel(f"Мой вывод: {dossier_output_summary(links)}"))
        card_layout.addWidget(
            QLabel("Где использовать: идея, задача, карта, объект или заметка, если вы уже связали досье.")
        )
        card_layout.addWidget(QLabel("Следующие действия: свяжите запись с рабочими сущностями проекта."))
        return card


__all__ = ["DossierDetailsDialog"]
