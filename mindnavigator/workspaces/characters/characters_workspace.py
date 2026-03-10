"""CharactersWorkspace class module for characters workspace."""

from __future__ import annotations

from typing import Optional

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

from mindnavigator.storage import CHARACTER_ENTITY_KINDS, CharacterData, get_database
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll


CHARACTER_LINK_KIND_LABELS = {
    "task": "Р—Р°РґР°С‡Р°",
    "project": "РџСЂРѕРµРєС‚",
    "note": "Р—Р°РјРµС‚РєР°",
    "idea": "РРґРµСЏ",
    "object": "РћР±СЉРµРєС‚",
    "map": "РљР°СЂС‚Р°",
    "marker": "РњРµС‚РєР° РєР°СЂС‚С‹",
    "file": "Р¤Р°Р№Р»",
    "collection_item": "Р­Р»РµРјРµРЅС‚ РєРѕР»Р»РµРєС†РёРё",
    "collection_category": "РљР°С‚РµРіРѕСЂРёСЏ РєРѕР»Р»РµРєС†РёРё",
    "shop_category": "РљР°С‚РµРіРѕСЂРёСЏ РїРѕРєСѓРїРѕРє",
    "shop_item": "РџРѕРєСѓРїРєР°",
    "shop_source": "РСЃС‚РѕС‡РЅРёРє С†РµРЅС‹",
    "wishlist": "Р’РёС€Р»РёСЃС‚",
}


class CharactersWorkspace(QWidget):
    """Character mode with editable cards and links to any app entity."""

    workspace_id = "characters"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._characters_by_id: dict[int, CharacterData] = {}
        self._current_character_id: Optional[int] = None
        self._entity_filter_kind: Optional[str] = None
        self._entity_filter_id: Optional[int] = None
        self._loading_details = False
        self._build_ui()
        self.refresh_characters()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        title = QLabel("РџРµСЂСЃРѕРЅР°Р¶Рё")
        title.setObjectName("CharactersTitle")
        self.search_input = QLineEdit()
        self.search_input.setObjectName("CharactersSearch")
        self.search_input.setPlaceholderText("РџРѕРёСЃРє РїРѕ РёРјРµРЅРё, СЂРѕР»Рё, С‚РµРіР°Рј Рё РѕРїРёСЃР°РЅРёСЋ")

        self.add_button = QToolButton()
        self.add_button.setObjectName("CharactersPrimaryButton")
        self.add_button.setText("РќРѕРІС‹Р№")
        self.delete_button = QToolButton()
        self.delete_button.setObjectName("CharactersDangerButton")
        self.delete_button.setText("РЈРґР°Р»РёС‚СЊ")

        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.search_input, 1)
        header_layout.addWidget(self.add_button)
        header_layout.addWidget(self.delete_button)
        root_layout.addLayout(header_layout)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter, 1)

        list_container = QFrame()
        list_container.setObjectName("CharactersListContainer")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(8)
        list_title = QLabel("РЎРїРёСЃРѕРє РїРµСЂСЃРѕРЅР°Р¶РµР№")
        list_title.setObjectName("CharactersSectionTitle")
        self.characters_list = QListWidget()
        self.characters_list.setObjectName("CharactersList")
        self.characters_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_layout.addWidget(list_title)
        list_layout.addWidget(self.characters_list, 1)
        splitter.addWidget(list_container)

        details_container = QFrame()
        details_container.setObjectName("CharactersDetailsContainer")
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(10)

        details_top_layout = QHBoxLayout()
        details_top_layout.setSpacing(8)
        details_title = QLabel("РљР°СЂС‚РѕС‡РєР° РїРµСЂСЃРѕРЅР°Р¶Р°")
        details_title.setObjectName("CharactersSectionTitle")
        self.filter_label = QLabel("Р¤РёР»СЊС‚СЂ: РІСЃРµ СЃСѓС‰РЅРѕСЃС‚Рё")
        self.filter_label.setObjectName("CharactersHint")
        details_top_layout.addWidget(details_title)
        details_top_layout.addStretch(1)
        details_top_layout.addWidget(self.filter_label)
        details_layout.addLayout(details_top_layout)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.role_edit = QLineEdit()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ")
        self.description_edit = QPlainTextEdit()
        self.description_edit.setMinimumHeight(130)
        form.addRow("РРјСЏ", self.name_edit)
        form.addRow("Р РѕР»СЊ", self.role_edit)
        form.addRow("РўРµРіРё", self.tags_edit)
        form.addRow("РћРїРёСЃР°РЅРёРµ", self.description_edit)
        details_layout.addLayout(form)

        details_actions_layout = QHBoxLayout()
        details_actions_layout.setSpacing(8)
        self.save_button = QToolButton()
        self.save_button.setObjectName("CharactersPrimaryButton")
        self.save_button.setText("РЎРѕС…СЂР°РЅРёС‚СЊ")
        details_actions_layout.addWidget(self.save_button)
        details_actions_layout.addStretch(1)
        details_layout.addLayout(details_actions_layout)

        links_title_layout = QHBoxLayout()
        links_title_layout.setSpacing(8)
        links_title = QLabel("РЎРІСЏР·Р°РЅРЅС‹Рµ СЃСѓС‰РЅРѕСЃС‚Рё")
        links_title.setObjectName("CharactersSectionTitle")
        self.add_link_button = QToolButton()
        self.add_link_button.setObjectName("CharactersPrimaryButton")
        self.add_link_button.setText("Р”РѕР±Р°РІРёС‚СЊ СЃРІСЏР·СЊ")
        self.remove_link_button = QToolButton()
        self.remove_link_button.setObjectName("CharactersDangerButton")
        self.remove_link_button.setText("РЈРґР°Р»РёС‚СЊ СЃРІСЏР·СЊ")
        links_title_layout.addWidget(links_title)
        links_title_layout.addStretch(1)
        links_title_layout.addWidget(self.add_link_button)
        links_title_layout.addWidget(self.remove_link_button)
        details_layout.addLayout(links_title_layout)

        self.links_list = QListWidget()
        self.links_list.setObjectName("CharactersLinksList")
        self.links_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        details_layout.addWidget(self.links_list, 1)
        splitter.addWidget(details_container)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.characters_list),
            attach_smooth_scroll(self.links_list),
            attach_smooth_scroll(self.description_edit),
        ]

        self.search_input.textChanged.connect(lambda _text: self.refresh_characters())
        self.add_button.clicked.connect(self._add_character)
        self.delete_button.clicked.connect(self._delete_current_character)
        self.characters_list.currentItemChanged.connect(self._on_character_selection_changed)
        self.save_button.clicked.connect(self._save_current_character)
        self.add_link_button.clicked.connect(self._open_add_link_dialog)
        self.remove_link_button.clicked.connect(self._remove_selected_link)
        self.links_list.itemDoubleClicked.connect(self._show_selected_link_info)

        self._set_details_enabled(False)
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#CharactersTitle {
                color: #e6e6e6;
                font-size: 20px;
                font-weight: 600;
            }
            QLabel#CharactersSectionTitle {
                color: #d8dbe3;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#CharactersHint {
                color: #8f95a1;
                font-size: 11px;
            }
            QLineEdit#CharactersSearch,
            QFrame#CharactersDetailsContainer QLineEdit,
            QFrame#CharactersDetailsContainer QPlainTextEdit {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                color: #e6e6e6;
                padding: 6px 8px;
            }
            QFrame#CharactersListContainer,
            QFrame#CharactersDetailsContainer {
                background: #171a20;
                border: 1px solid #2f333b;
                border-radius: 10px;
            }
            QListWidget#CharactersList,
            QListWidget#CharactersLinksList {
                background: #111318;
                border: 1px solid #2b3038;
                border-radius: 8px;
                color: #e6e6e6;
            }
            QListWidget#CharactersList::item,
            QListWidget#CharactersLinksList::item {
                padding: 7px 8px;
            }
            QListWidget#CharactersList::item:selected,
            QListWidget#CharactersLinksList::item:selected {
                background: #2d3440;
                border-radius: 6px;
            }
            QToolButton#CharactersPrimaryButton,
            QToolButton#CharactersDangerButton {
                background: #2a2f37;
                border: 1px solid #3a404a;
                border-radius: 6px;
                color: #e6e6e6;
                padding: 6px 12px;
            }
            QToolButton#CharactersPrimaryButton:hover {
                background: #333a45;
            }
            QToolButton#CharactersDangerButton {
                background: #3a2525;
                border-color: #4d2f2f;
            }
            QToolButton#CharactersDangerButton:hover {
                background: #4a2f2f;
            }
            """
        )

    def _set_details_enabled(self, enabled: bool) -> None:
        self.delete_button.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        self.role_edit.setEnabled(enabled)
        self.tags_edit.setEnabled(enabled)
        self.description_edit.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.add_link_button.setEnabled(enabled)
        self.remove_link_button.setEnabled(enabled and self.links_list.currentItem() is not None)
        self.links_list.setEnabled(enabled)

    def _tags_to_text(self, tags: list[str]) -> str:
        return ", ".join(tags)

    @staticmethod
    def _parse_tags(text: str) -> list[str]:
        result: list[str] = []
        for raw_tag in (text or "").split(","):
            tag = raw_tag.strip()
            if tag and tag not in result:
                result.append(tag)
        return result

    def set_entity_filter(self, entity_kind: Optional[str], entity_id: Optional[int]) -> None:
        self._entity_filter_kind = entity_kind
        self._entity_filter_id = entity_id
        if entity_kind and entity_id is not None:
            target = self._db.describe_character_link_target(entity_kind, int(entity_id))
            self.filter_label.setText(f"Р¤РёР»СЊС‚СЂ: {target}")
        else:
            self.filter_label.setText("Р¤РёР»СЊС‚СЂ: РІСЃРµ СЃСѓС‰РЅРѕСЃС‚Рё")
        self.refresh_characters()

    def refresh_characters(self) -> None:
        selected_id = self._current_character_id
        search_text = self.search_input.text().strip()
        characters = self._db.fetch_characters(
            search_text=search_text,
            linked_entity_kind=self._entity_filter_kind,
            linked_entity_id=self._entity_filter_id,
        )
        self._characters_by_id = {character.id: character for character in characters}
        self.characters_list.blockSignals(True)
        self.characters_list.clear()
        for character in characters:
            label = character.name
            if character.role:
                label = f"{label} В· {character.role}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, character.id)
            if character.description:
                item.setToolTip(character.description)
            self.characters_list.addItem(item)
        self.characters_list.blockSignals(False)

        restored = False
        if selected_id is not None:
            restored = self.focus_character(selected_id, refresh=False)
        if not restored and self.characters_list.count() > 0:
            self.characters_list.setCurrentRow(0)
        if self.characters_list.count() == 0:
            self._current_character_id = None
            self._clear_details()
            self._set_details_enabled(False)

    def focus_character(self, character_id: int, *, refresh: bool = True) -> bool:
        if refresh:
            self.refresh_characters()
        for row in range(self.characters_list.count()):
            item = self.characters_list.item(row)
            if item is None:
                continue
            if int(item.data(Qt.ItemDataRole.UserRole)) == int(character_id):
                self.characters_list.setCurrentItem(item)
                self.characters_list.scrollToItem(item)
                return True
        return False

    def _clear_details(self) -> None:
        self._loading_details = True
        self.name_edit.clear()
        self.role_edit.clear()
        self.tags_edit.clear()
        self.description_edit.clear()
        self.links_list.clear()
        self._loading_details = False

    def _on_character_selection_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if current is None:
            self._current_character_id = None
            self._clear_details()
            self._set_details_enabled(False)
            return
        character_id = int(current.data(Qt.ItemDataRole.UserRole))
        self._current_character_id = character_id
        character = self._characters_by_id.get(character_id)
        if character is None:
            self._clear_details()
            self._set_details_enabled(False)
            return
        self._loading_details = True
        self.name_edit.setText(character.name)
        self.role_edit.setText(character.role)
        self.tags_edit.setText(self._tags_to_text(character.tags))
        self.description_edit.setPlainText(character.description)
        self._loading_details = False
        self._load_links(character_id)
        self._set_details_enabled(True)

    def _load_links(self, character_id: int) -> None:
        links = self._db.fetch_character_links(character_id)
        self.links_list.clear()
        for link in links:
            kind_label = CHARACTER_LINK_KIND_LABELS.get(link.entity_kind, link.entity_kind)
            target_label = self._db.describe_character_link_target(link.entity_kind, link.entity_id)
            item = QListWidgetItem(f"{kind_label}: {target_label}")
            item.setData(Qt.ItemDataRole.UserRole, link.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, link.entity_kind)
            item.setData(Qt.ItemDataRole.UserRole + 2, link.entity_id)
            self.links_list.addItem(item)
        self.remove_link_button.setEnabled(self.links_list.currentItem() is not None)

    def _add_character(self) -> None:
        try:
            character = self._db.create_character(name="РќРѕРІС‹Р№ РїРµСЂСЃРѕРЅР°Р¶")
        except ValueError as exc:
            QMessageBox.warning(self, "РџРµСЂСЃРѕРЅР°Р¶Рё", str(exc))
            return
        self.refresh_characters()
        self.focus_character(character.id, refresh=False)

    def _delete_current_character(self) -> None:
        if self._current_character_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "РЈРґР°Р»РµРЅРёРµ",
            "РЈРґР°Р»РёС‚СЊ РїРµСЂСЃРѕРЅР°Р¶Р° Рё РІСЃРµ РµРіРѕ СЃРІСЏР·Рё?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_character(self._current_character_id)
        self.refresh_characters()

    def _save_current_character(self) -> None:
        if self._loading_details or self._current_character_id is None:
            return
        try:
            updated = self._db.update_character(
                self._current_character_id,
                name=self.name_edit.text(),
                role=self.role_edit.text(),
                description=self.description_edit.toPlainText(),
                tags=self._parse_tags(self.tags_edit.text()),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "РџРµСЂСЃРѕРЅР°Р¶Рё", str(exc))
            return
        self._characters_by_id[updated.id] = updated
        self.refresh_characters()
        self.focus_character(updated.id, refresh=False)

    def _kind_choices(self) -> list[tuple[str, str]]:
        choices: list[tuple[str, str]] = []
        for kind in CHARACTER_ENTITY_KINDS:
            choices.append((CHARACTER_LINK_KIND_LABELS.get(kind, kind), kind))
        return choices

    def _open_add_link_dialog(self) -> None:
        if self._current_character_id is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Р”РѕР±Р°РІРёС‚СЊ СЃРІСЏР·СЊ")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()

        kind_combo = QComboBox(dialog)
        for label, kind in self._kind_choices():
            kind_combo.addItem(label, kind)

        search_edit = QLineEdit(dialog)
        search_edit.setPlaceholderText("Р¤РёР»СЊС‚СЂ РїРѕ РЅР°Р·РІР°РЅРёСЋ СЃСѓС‰РЅРѕСЃС‚Рё")

        entity_combo = QComboBox(dialog)

        def fill_entities() -> None:
            entity_combo.clear()
            selected_kind = str(kind_combo.currentData() or "")
            options = self._db.fetch_character_link_options(selected_kind, search_edit.text())
            if not options:
                entity_combo.addItem("вЂ” РЅРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… вЂ”", None)
                return
            for entity_id, label in options:
                entity_combo.addItem(label, entity_id)

        kind_combo.currentIndexChanged.connect(lambda _index: fill_entities())
        search_edit.textChanged.connect(lambda _text: fill_entities())
        fill_entities()

        form.addRow("РўРёРї СЃСѓС‰РЅРѕСЃС‚Рё", kind_combo)
        form.addRow("РџРѕРёСЃРє", search_edit)
        form.addRow("РЎСѓС‰РЅРѕСЃС‚СЊ", entity_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        entity_id = entity_combo.currentData()
        if entity_id is None:
            QMessageBox.warning(self, "РџРµСЂСЃРѕРЅР°Р¶Рё", "РќРµС‚ РґРѕСЃС‚СѓРїРЅРѕР№ СЃСѓС‰РЅРѕСЃС‚Рё РґР»СЏ РїСЂРёРІСЏР·РєРё.")
            return
        try:
            self._db.add_character_link(
                self._current_character_id,
                str(kind_combo.currentData() or ""),
                int(entity_id),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "РџРµСЂСЃРѕРЅР°Р¶Рё", str(exc))
            return
        self._load_links(self._current_character_id)
        self.refresh_characters()
        self.focus_character(self._current_character_id, refresh=False)

    def _remove_selected_link(self) -> None:
        if self._current_character_id is None:
            return
        item = self.links_list.currentItem()
        if item is None:
            return
        link_id = int(item.data(Qt.ItemDataRole.UserRole))
        self._db.delete_character_link(link_id)
        self._load_links(self._current_character_id)
        self.refresh_characters()
        self.focus_character(self._current_character_id, refresh=False)

    def _show_selected_link_info(self, item: QListWidgetItem) -> None:
        entity_kind = str(item.data(Qt.ItemDataRole.UserRole + 1) or "")
        entity_id = int(item.data(Qt.ItemDataRole.UserRole + 2) or 0)
        kind_label = CHARACTER_LINK_KIND_LABELS.get(entity_kind, entity_kind)
        target_label = self._db.describe_character_link_target(entity_kind, entity_id)
        QMessageBox.information(
            self,
            "РЎРІСЏР·СЊ РїРµСЂСЃРѕРЅР°Р¶Р°",
            f"{kind_label}\n{target_label}",
        )


__all__ = ["CharactersWorkspace"]
