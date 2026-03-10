"""MindDrawEntityPickerDialog class module for minddraw workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class MindDrawEntityPickerDialog(QDialog):
    """Simple picker for selecting external entities for node binding."""

    ENTITY_KINDS: list[tuple[str, str]] = [
        ("task", "Задачи"),
        ("project", "Проекты"),
        ("idea", "Идеи"),
        ("note", "Заметки"),
        ("map", "Карты"),
        ("object", "Объекты"),
        ("character", "Персонажи"),
        ("file", "Файлы"),
        ("collection", "Коллекции"),
        ("purchase", "Покупки"),
    ]

    def __init__(self, fetch_callback: Callable[[str, str], list[EntityOption]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fetch_callback = fetch_callback
        self._selected_option: Optional[EntityOption] = None
        self.setWindowTitle("Привязать сущность")
        self.setObjectName("MindDrawEntityPicker")
        self.setProperty("dialog_category", "minimal_flex")
        self.resize(620, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        form = QFormLayout()
        self.kind_combo = QComboBox()
        for kind_key, title in self.ENTITY_KINDS:
            self.kind_combo.addItem(title, kind_key)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск сущности…")
        form.addRow("Режим", self.kind_combo)
        form.addRow("Поиск", self.search_edit)
        layout.addLayout(form)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(lambda _item: self._accept_if_selected())
        layout.addWidget(self.list_widget, 1)

        button_row = QHBoxLayout()
        self.reload_btn = QPushButton("Обновить")
        self.reload_btn.clicked.connect(self._reload)
        button_row.addWidget(self.reload_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.kind_combo.currentIndexChanged.connect(self._reload)
        self.search_edit.textChanged.connect(self._reload)
        self._reload()

    def selected_option(self) -> Optional[EntityOption]:
        return self._selected_option

    def _accept_if_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "MindDraw", "Выберите сущность для привязки.")
            return
        option = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(option, EntityOption):
            return
        self._selected_option = option
        self.accept()

    def _reload(self) -> None:
        kind = str(self.kind_combo.currentData() or "")
        query = (self.search_edit.text() or "").strip()
        options = self._fetch_callback(kind, query)
        self.list_widget.clear()
        for option in options:
            subtitle = f" · {option.subtitle}" if option.subtitle else ""
            label = f"{option.title}{subtitle}"
            row = QListWidgetItem(label)
            row.setData(Qt.ItemDataRole.UserRole, option)
            self.list_widget.addItem(row)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

__all__ = ["MindDrawEntityPickerDialog"]
