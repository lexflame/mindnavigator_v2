"""Dialog to add a purchase item by URL with preview."""

from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
)

from mindnavigator.http_client import HttpClient, HttpClientError
from mindnavigator.shop_parsing import ParsedShopResult, ShopParseService
from mindnavigator.shop_parsers import build_default_parsers
from mindnavigator.storage import Database, ShopItemData, ShopSourceData
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


@dataclass(frozen=True)
class PurchaseAddResult:
    item: ShopItemData
    source: ShopSourceData


class PurchaseAddByUrlDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._parsed_ok = False
        self._shop_code = ""
        self._preview_title = ""
        self._parsed_result: ParsedShopResult | None = None
        self._result: Optional[PurchaseAddResult] = None
        self._http = HttpClient(
            timeout=15.0,
            max_retries=2,
            backoff_seconds=1.5,
            user_agent="MindNavigator/ShopParser",
            on_error=self._set_status,
        )
        self._parse_service = ShopParseService(self._db, build_default_parsers(self._http))

        self.setObjectName("PurchaseAddByUrlDialog")
        self.setWindowTitle("Добавить товар по URL")
        self.setProperty("dialog_category", "minimal_flex")
        self.setMinimumSize(760, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_label = QLabel("Добавить товар по URL")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://магазин/товар")
        self.parse_button = QToolButton()
        self.parse_button.setText("Парсить")
        self.parse_button.setObjectName("PurchaseParseButton")
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.parse_button)
        layout.addLayout(url_row)
        parse_hint = QLabel("Enter или кнопка «Парсить» для предпросмотра")
        parse_hint.setObjectName("PurchaseParseHint")
        layout.addWidget(parse_hint)

        self.preview_box = QGroupBox("Предпросмотр")
        preview_layout = QFormLayout(self.preview_box)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)
        self.preview_title = QLabel("—")
        self.preview_shop = QLabel("—")
        self.preview_price = QLabel("—")
        self.preview_stock = QLabel("—")
        self.preview_sku = QLabel("—")
        for label in (
            self.preview_title,
            self.preview_shop,
            self.preview_price,
            self.preview_stock,
            self.preview_sku,
        ):
            label.setWordWrap(True)
        preview_layout.addRow("Название", self.preview_title)
        preview_layout.addRow("Магазин", self.preview_shop)
        preview_layout.addRow("Цена", self.preview_price)
        preview_layout.addRow("Наличие", self.preview_stock)
        preview_layout.addRow("Артикул", self.preview_sku)
        layout.addWidget(self.preview_box)

        category_box = QGroupBox("Категория")
        category_layout = QVBoxLayout(category_box)
        category_layout.setContentsMargins(12, 12, 12, 12)
        category_layout.setSpacing(8)
        category_controls = QHBoxLayout()
        self.category_add_btn = QToolButton()
        self.category_add_btn.setText("Добавить")
        self.category_rename_btn = QToolButton()
        self.category_rename_btn.setText("Переименовать")
        self.category_delete_btn = QToolButton()
        self.category_delete_btn.setText("Удалить")
        category_controls.addWidget(self.category_add_btn)
        category_controls.addWidget(self.category_rename_btn)
        category_controls.addWidget(self.category_delete_btn)
        category_controls.addStretch(1)
        category_layout.addLayout(category_controls)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderHidden(True)
        category_layout.addWidget(self.category_tree, 1)
        layout.addWidget(category_box)

        attach_box = QGroupBox("Привязка товара")
        attach_layout = QVBoxLayout(attach_box)
        attach_layout.setContentsMargins(12, 12, 12, 12)
        attach_layout.setSpacing(8)

        self.mode_group = QButtonGroup(self)
        self.mode_new = QRadioButton("Создать новый товар")
        self.mode_existing = QRadioButton("Привязать к существующему")
        self.mode_new.setChecked(True)
        self.mode_group.addButton(self.mode_new)
        self.mode_group.addButton(self.mode_existing)
        attach_layout.addWidget(self.mode_new)
        attach_layout.addWidget(self.mode_existing)

        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText("Название товара")
        attach_layout.addWidget(self.new_title)

        self.existing_combo = QComboBox()
        self.existing_combo.setEnabled(False)
        attach_layout.addWidget(self.existing_combo)
        layout.addWidget(attach_box)

        self.status_label = QLabel("")
        self.status_label.setObjectName("PurchaseDialogStatus")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self._save_button = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._save_button.setText("Сохранить")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._save_button.setEnabled(False)

        self.url_input.returnPressed.connect(self._parse_url)
        self.parse_button.clicked.connect(self._parse_url)
        self.mode_group.buttonToggled.connect(self._sync_mode)
        self.category_add_btn.clicked.connect(self._add_category)
        self.category_rename_btn.clicked.connect(self._rename_category)
        self.category_delete_btn.clicked.connect(self._delete_category)
        self.category_tree.itemSelectionChanged.connect(self._refresh_save_state)
        self._load_existing_items()
        self._load_categories()
        self._set_category_enabled(False)
        self._sync_mode()

        self.setStyleSheet(f"""
            QDialog#PurchaseAddByUrlDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#PurchaseAddByUrlDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#PurchaseAddByUrlDialog QLabel {{
                color: #e0e0e0;
                font-size: 13px;
            }}
            QDialog#PurchaseAddByUrlDialog QLineEdit,
            QDialog#PurchaseAddByUrlDialog QComboBox {{
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}
            QDialog#PurchaseAddByUrlDialog QGroupBox {{
                border: 1px solid #2a2b2f;
                border-radius: 8px;
                margin-top: 10px;
            }}
            QDialog#PurchaseAddByUrlDialog QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px;
                color: #cfcfcf;
            }}
            QDialog#PurchaseAddByUrlDialog QRadioButton {{
                color: #cfcfcf;
                padding: 2px 0;
            }}
            QDialog#PurchaseAddByUrlDialog QDialogButtonBox QPushButton,
            QDialog#PurchaseAddByUrlDialog QToolButton#PurchaseParseButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 110px;
                min-height: 32px;
            }}
            QDialog#PurchaseAddByUrlDialog QDialogButtonBox QPushButton:hover,
            QDialog#PurchaseAddByUrlDialog QToolButton#PurchaseParseButton:hover {{
                background: #34363b;
            }}
            QLabel#PurchaseDialogStatus {{
                color: #b4bac3;
            }}
            QLabel#PurchaseParseHint {{
                color: #8b92a0;
            }}
        """)

    def _load_existing_items(self) -> None:
        self.existing_combo.clear()
        items = self._db.fetch_shop_items()
        if not items:
            self.existing_combo.addItem("Нет товаров", None)
            self.existing_combo.setEnabled(False)
            return
        self.existing_combo.setEnabled(True)
        for item in items:
            self.existing_combo.addItem(item.title, item.id)

    def _sync_mode(self, *_) -> None:
        is_new = self.mode_new.isChecked()
        self.new_title.setEnabled(is_new)
        self.existing_combo.setEnabled(not is_new and self.existing_combo.count() > 0)
        self._refresh_save_state()

    def _refresh_save_state(self) -> None:
        if not self._parsed_ok:
            self._save_button.setEnabled(False)
            return
        if self._selected_category_id() is None and not self._category_has_uncategorized():
            self._save_button.setEnabled(False)
            return
        if self.mode_new.isChecked():
            self._save_button.setEnabled(True)
            return
        selected = self.existing_combo.currentData()
        self._save_button.setEnabled(selected is not None)

    def _parse_url(self) -> None:
        url = (self.url_input.text() or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            self._set_status("Нужен корректный URL (http/https).")
            self._parsed_ok = False
            self._refresh_save_state()
            return
        try:
            parser = self._parse_service.resolve_parser(url)
            result = parser.parse(url)
        except (ValueError, HttpClientError) as exc:
            # Fallback: allow manual save without parser data.
            parsed = urlparse(url)
            shop = parsed.netloc.lower() or "unknown"
            result = ParsedShopResult(
                title="",
                sku="",
                price=None,
                currency="",
                in_stock=False,
                stock_text="",
                category_hint="",
                properties=[],
                images=[],
                shop_code=shop,
                canonical_url=url,
                raw={"error": str(exc)},
            )
            self._set_status("Парсер не найден — сохранение без парсинга.")

        self._parsed_result = result
        self._shop_code = result.shop_code or urlparse(url).netloc.lower()
        title = result.title or (urlparse(url).path.strip("/").split("/")[-1] or self._shop_code)
        title = title.replace("-", " ").replace("_", " ").strip() or self._shop_code
        self._preview_title = title
        self.preview_title.setText(title)
        self.preview_shop.setText(result.shop_code or self._shop_code)
        price_text = "—"
        if result.price is not None:
            price_text = f"{result.price:.2f} {result.currency}".strip()
        self.preview_price.setText(price_text)
        self.preview_stock.setText(result.stock_text or ("В наличии" if result.in_stock else "Нет в наличии"))
        self.preview_sku.setText(result.sku or "—")
        if not self.new_title.text().strip():
            self.new_title.setText(title)
        self._parsed_ok = True
        self._set_category_enabled(True)
        self._set_status("Предпросмотр готов. Можно сохранить.")
        self._refresh_save_state()

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_accept(self) -> None:
        if not self._parsed_ok:
            self._parse_url()
        if not self._parsed_ok:
            self._set_status("Сначала выполните предпросмотр.")
            return
        url = (self.url_input.text() or "").strip()
        category_id = self._selected_category_id()
        parsed = self._parsed_result or ParsedShopResult(shop_code=self._shop_code, canonical_url=url)
        if self.mode_new.isChecked():
            title = (self.new_title.text() or "").strip() or self._preview_title or url
            item = self._db.create_shop_item(title, category_id=category_id)
        else:
            item_id = self.existing_combo.currentData()
            if item_id is None:
                self._set_status("Выберите товар для привязки.")
                return
            item = self._db.get_shop_item(int(item_id))
            if item is None:
                self._set_status("Товар не найден.")
                return
            self._db.update_shop_item_category(item.id, category_id)

        parsed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        raw_payload = parsed.raw if parsed.raw is not None else {"url": url, "shop_code": self._shop_code}
        source = self._db.upsert_shop_source(
            item_id=item.id,
            shop_code=parsed.shop_code or self._shop_code,
            url=parsed.canonical_url or url,
            sku=parsed.sku,
            currency=parsed.currency,
            price=parsed.price,
            in_stock=parsed.in_stock,
            stock_text=parsed.stock_text,
            parsed_at=parsed_at,
            raw_json=json.dumps(raw_payload, ensure_ascii=False),
        )
        self._db.add_shop_price_history(
            source_id=source.id,
            price=parsed.price,
            currency=parsed.currency,
            in_stock=parsed.in_stock,
            captured_at=parsed_at,
        )
        if parsed.properties:
            from mindnavigator.storage import ShopSourcePropertyData

            props = [
                ShopSourcePropertyData(
                    id=0,
                    source_id=source.id,
                    name=p.name,
                    value=p.value,
                    unit=p.unit,
                    normalized_key=p.normalized_key,
                )
                for p in parsed.properties
            ]
            self._db.replace_shop_source_properties(source.id, props)

        self._result = PurchaseAddResult(item=item, source=source)
        self.accept()

    def result_payload(self) -> Optional[PurchaseAddResult]:
        return self._result

    def _load_categories(self) -> None:
        self.category_tree.clear()
        root = QTreeWidgetItem(["Без категории"])
        root.setData(0, Qt.ItemDataRole.UserRole, None)
        self.category_tree.addTopLevelItem(root)
        categories = self._db.fetch_shop_categories()
        by_parent: dict[Optional[int], list] = {}
        for cat in categories:
            by_parent.setdefault(cat.parent_id, []).append(cat)

        def add_children(parent_item: QTreeWidgetItem, parent_id: Optional[int]) -> None:
            for category_row in sorted(by_parent.get(parent_id, []), key=lambda c: c.title.lower()):
                category_item = QTreeWidgetItem([category_row.title])
                category_item.setData(0, Qt.ItemDataRole.UserRole, category_row.id)
                parent_item.addChild(category_item)
                add_children(category_item, category_row.id)

        for cat in sorted(by_parent.get(None, []), key=lambda c: c.title.lower()):
            item = QTreeWidgetItem([cat.title])
            item.setData(0, Qt.ItemDataRole.UserRole, cat.id)
            self.category_tree.addTopLevelItem(item)
            add_children(item, cat.id)
        self.category_tree.expandAll()
        self.category_tree.setCurrentItem(root)

    def _selected_category_id(self) -> Optional[int]:
        item = self.category_tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _category_has_uncategorized(self) -> bool:
        return self.category_tree.topLevelItemCount() > 0

    def _set_category_enabled(self, enabled: bool) -> None:
        self.category_tree.setEnabled(enabled)
        self.category_add_btn.setEnabled(enabled)
        self.category_rename_btn.setEnabled(enabled)
        self.category_delete_btn.setEnabled(enabled)

    def _add_category(self) -> None:
        title, ok = QInputDialog.getText(self, "Новая категория", "Название:")
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        parent_id = self._selected_category_id()
        self._db.create_shop_category(title, parent_id=parent_id)
        self._load_categories()

    def _rename_category(self) -> None:
        current = self.category_tree.currentItem()
        if current is None:
            return
        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if category_id is None:
            QMessageBox.information(self, "Категория", "Нельзя переименовать «Без категории».")
            return
        title, ok = QInputDialog.getText(self, "Переименовать", "Новое название:", text=current.text(0))
        if not ok:
            return
        title = (title or "").strip()
        if not title:
            return
        self._db.update_shop_category_title(int(category_id), title)
        self._load_categories()

    def _delete_category(self) -> None:
        current = self.category_tree.currentItem()
        if current is None:
            return
        category_id = current.data(0, Qt.ItemDataRole.UserRole)
        if category_id is None:
            QMessageBox.information(self, "Категория", "Нельзя удалить «Без категории».")
            return
        confirm = QMessageBox.question(
            self,
            "Удалить категорию",
            "Удалить категорию? Все товары будут без категории.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_shop_category(int(category_id))
        self._load_categories()
