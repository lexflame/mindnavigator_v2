"""Read-only details dialog for a Dossier item."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403


class DossierDetailsDialog(QDialog):
    def __init__(self, dossier: DossierData, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._dossier = dossier
        self.setWindowTitle("Подробности досье")
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
        header.addWidget(title_label, 1)
        header.addWidget(meta_label)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_summary_card())
        content_layout.addWidget(self._build_properties_card())
        content_layout.addWidget(self._build_metadata_card())
        content_layout.addWidget(self._build_links_card())
        content_layout.addStretch(1)

        scroll.setWidget(content)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog#DossierDetailsDialog {
                background: #171a20;
                color: #e6e6e6;
            }
            QDialog#DossierDetailsDialog QLabel {
                color: #d9dde4;
            }
            QLabel#DossierDetailsTitle {
                color: #f3f5f8;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#DossierDetailsMeta {
                background: #232831;
                border: 1px solid #313844;
                border-radius: 12px;
                padding: 6px 12px;
            }
            QFrame#DossierDetailsCard {
                background: #1d2027;
                border: 1px solid #2e323b;
                border-radius: 10px;
            }
            QLabel#DossierDetailsSectionTitle {
                color: #f3f5f8;
                font-weight: 600;
            }
            QDialog#DossierDetailsDialog QPlainTextEdit,
            QDialog#DossierDetailsDialog QListWidget {
                background: #20242c;
                color: #e6e6e6;
                border: 1px solid #343944;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QDialog#DossierDetailsDialog QDialogButtonBox QPushButton {
                background: #2b313b;
                color: #e6e6e6;
                border: 1px solid #3b4351;
                border-radius: 8px;
                padding: 8px 14px;
            }
            """
        )

    def _build_summary_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DossierDetailsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title = QLabel("Описание")
        title.setObjectName("DossierDetailsSectionTitle")
        card_layout.addWidget(title)

        summary = QLabel(self._dossier.summary or "Краткое описание пока не заполнено.")
        summary.setWordWrap(True)
        card_layout.addWidget(summary)

        description = QPlainTextEdit()
        description.setReadOnly(True)
        description.setPlainText(self._dossier.description or "")
        description.setMinimumHeight(180)
        card_layout.addWidget(description)
        return card

    def _build_properties_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DossierDetailsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title = QLabel("Свойства")
        title.setObjectName("DossierDetailsSectionTitle")
        card_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        form.addRow("Вид", QLabel(dossier_kind_label(self._dossier.kind)))
        form.addRow("Статус", QLabel(dossier_status_label(self._dossier.status)))
        form.addRow("Рейтинг", QLabel(dossier_rating_label(self._dossier.rating)))
        form.addRow("Теги", QLabel(dossier_tags_text(self._dossier.tags)))
        form.addRow("Источник", QLabel(self._dossier.source or "Не указан"))
        form.addRow("Обложка / изображение", QLabel(self._dossier.cover_image or "Не указано"))
        form.addRow("Создано", QLabel(self._dossier.created_at or "—"))
        form.addRow("Обновлено", QLabel(self._dossier.updated_at or "—"))
        card_layout.addLayout(form)
        return card

    def _build_metadata_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DossierDetailsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title = QLabel("Типовые поля")
        title.setObjectName("DossierDetailsSectionTitle")
        card_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)

        has_rows = False
        for field_name in DossierData.METADATA_FIELDS[self._dossier.kind]:
            value = self._dossier.metadata.get(field_name)
            if value in (None, "", []):
                continue
            label_text = DOSSIER_METADATA_LABELS.get(field_name, field_name.replace("_", " ").title())
            form.addRow(label_text, QLabel(render_list_value(value)))
            has_rows = True
        if not has_rows:
            form.addRow("Поля", QLabel("Типовые поля пока не заполнены."))

        card_layout.addLayout(form)
        return card

    def _build_links_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DossierDetailsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        title = QLabel("Связанные сущности")
        title.setObjectName("DossierDetailsSectionTitle")
        card_layout.addWidget(title)

        links_list = QListWidget()
        links = self._db.fetch_dossier_links(self._dossier.id)
        if links:
            for link in links:
                label = self._db.describe_dossier_link_target(link.entity_kind, link.entity_id)
                links_list.addItem(QListWidgetItem(label))
        else:
            placeholder = QListWidgetItem("Связей пока нет")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            links_list.addItem(placeholder)
        card_layout.addWidget(links_list)
        return card


__all__ = ["DossierDetailsDialog"]
