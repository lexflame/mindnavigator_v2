"""Shared imports and helpers for the Dossier workspace."""

from __future__ import annotations

import sys
from typing import Any, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.storage import DossierData, DossierLinkData, get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay, show_dialog_standard
from mindnavigator.ui.styles import (
    build_popup_menu_stylesheet,
    build_scrollbar_stylesheet,
    get_scrollbar_tokens,
    get_theme_palette,
    normalize_theme_mode,
)
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace

_storage_get_database = get_database


def get_database():
    for module_name in ("mindnavigator.workspaces.dossier", "mindnavigator.workspaces.dossier.module_impl"):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        override = getattr(module, "get_database", None)
        if override is not None and override is not get_database:
            return override()
    return _storage_get_database()


DOSSIER_KIND_OPTIONS = [
    ("Все виды", None),
    ("Книга", "book"),
    ("Фильм", "film"),
    ("Игра", "game"),
    ("Писатель", "writer"),
]

DOSSIER_STATUS_OPTIONS = [
    ("Все статусы", None),
    ("Запланировано", "planned"),
    ("Активно", "active"),
    ("Завершено", "completed"),
    ("Пауза", "on_hold"),
    ("Архив", "archived"),
]

DOSSIER_RATING_OPTIONS = [("Любой рейтинг", None)] + [(f"{rating}/10", rating) for rating in range(10, 0, -1)]

DOSSIER_GROUP_OPTIONS = [
    ("Без групп", "none"),
    ("По виду", "kind"),
    ("По статусу", "status"),
    ("По рейтингу", "rating"),
]

DOSSIER_KIND_LABELS = {
    "book": "Книга",
    "film": "Фильм",
    "game": "Игра",
    "writer": "Писатель",
}

DOSSIER_STATUS_LABELS = {
    "planned": "Запланировано",
    "active": "Активно",
    "completed": "Завершено",
    "on_hold": "Пауза",
    "archived": "Архив",
}

DOSSIER_METADATA_LABELS = {
    "author_display": "Автор",
    "original_title": "Оригинал",
    "publication_year": "Год",
    "genre": "Жанр",
    "language": "Язык",
    "pages": "Страниц",
    "publisher": "Издатель",
    "series": "Серия",
    "isbn": "ISBN",
    "director": "Режиссёр",
    "release_year": "Релиз",
    "runtime_minutes": "Минуты",
    "country": "Страна",
    "franchise": "Франшиза",
    "format": "Формат",
    "age_rating": "Возраст",
    "developer": "Разработчик",
    "platforms": "Платформы",
    "engine": "Движок",
    "play_status": "Статус игры",
    "playtime_hours": "Часы",
    "birth_year": "Рождение",
    "death_year": "Смерть",
    "languages": "Языки",
    "primary_genres": "Жанры",
    "notable_works_summary": "Главные работы",
}

DOSSIER_KIND_COLORS = {
    "book": "#7290f2",
    "film": "#df7c4f",
    "game": "#4fb68a",
    "writer": "#b78cff",
}

DOSSIER_LINK_KIND_LABELS = {
    "task": "Задача",
    "map": "Карта",
    "marker": "Маркер",
    "note": "Заметка",
    "idea": "Идея",
    "object": "Объект",
    "character": "Персонаж",
}

DOSSIER_LINK_KIND_OPTIONS = [
    (DOSSIER_LINK_KIND_LABELS.get(kind, kind.title()), kind) for kind in DossierLinkData.SUPPORTED_ENTITY_KINDS
]


def dossier_kind_label(kind: str) -> str:
    return DOSSIER_KIND_LABELS.get((kind or "").strip().lower(), "Досье")


def dossier_status_label(status: str) -> str:
    return DOSSIER_STATUS_LABELS.get((status or "").strip().lower(), "Без статуса")


def dossier_rating_label(rating: Optional[int]) -> str:
    return f"{int(rating)}/10" if rating is not None else "Без оценки"


def dossier_tags_text(tags: list[str]) -> str:
    return ", ".join(tags) if tags else "Нет тегов"


def dossier_metadata_preview(dossier: DossierData, *, max_parts: int = 3) -> str:
    allowed_fields = DossierData.METADATA_FIELDS.get(dossier.kind, {})
    parts: list[str] = []
    for key in allowed_fields:
        value = dossier.metadata.get(key)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value[:3])
        else:
            rendered = str(value)
        label = DOSSIER_METADATA_LABELS.get(key, key.replace("_", " ").title())
        parts.append(f"{label}: {rendered}")
        if len(parts) >= max_parts:
            break
    return " • ".join(parts) if parts else "Детали пока не заполнены."


def dossier_secondary_line(dossier: DossierData) -> str:
    parts = [
        dossier_kind_label(dossier.kind),
        dossier_status_label(dossier.status),
        dossier_rating_label(dossier.rating),
    ]
    if dossier.source:
        parts.append(dossier.source)
    return " | ".join(part for part in parts if part)


def elided_text(metrics: QFontMetrics, text: str, width: int) -> str:
    return metrics.elidedText(text or "", Qt.TextElideMode.ElideRight, max(0, width))


def parse_tag_list(raw_value: str) -> list[str]:
    normalized: list[str] = []
    for raw_part in (raw_value or "").split(","):
        value = raw_part.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def render_list_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def resolve_theme_mode(widget: QWidget | None) -> str:
    return normalize_theme_mode(str(getattr(widget, "_theme_mode", "dark")))


__all__ = [
    "Any",
    "BaseWorkspace",
    "ConfirmDialog",
    "DossierData",
    "DossierLinkData",
    "DOSSIER_KIND_COLORS",
    "DOSSIER_KIND_LABELS",
    "DOSSIER_KIND_OPTIONS",
    "DOSSIER_GROUP_OPTIONS",
    "DOSSIER_LINK_KIND_LABELS",
    "DOSSIER_LINK_KIND_OPTIONS",
    "DOSSIER_METADATA_LABELS",
    "DOSSIER_RATING_OPTIONS",
    "DOSSIER_STATUS_LABELS",
    "DOSSIER_STATUS_OPTIONS",
    "Optional",
    "QAbstractItemView",
    "QAbstractListModel",
    "QAction",
    "QColor",
    "QComboBox",
    "QDialog",
    "QDialogButtonBox",
    "QFont",
    "QFontMetrics",
    "QFrame",
    "QFormLayout",
    "QHBoxLayout",
    "QLabel",
    "QLineEdit",
    "QListView",
    "QListWidget",
    "QListWidgetItem",
    "QMenu",
    "QModelIndex",
    "QMessageBox",
    "QPainter",
    "QPlainTextEdit",
    "QRect",
    "QScrollArea",
    "QSize",
    "QSpinBox",
    "QSplitter",
    "QStyle",
    "QStyledItemDelegate",
    "QStyleOptionViewItem",
    "QToolButton",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "dossier_kind_label",
    "dossier_metadata_preview",
    "dossier_rating_label",
    "dossier_secondary_line",
    "dossier_status_label",
    "dossier_tags_text",
    "elided_text",
    "exec_with_overlay",
    "build_popup_menu_stylesheet",
    "build_scrollbar_stylesheet",
    "get_database",
    "get_scrollbar_tokens",
    "get_theme_palette",
    "parse_tag_list",
    "resolve_theme_mode",
    "render_list_value",
    "show_dialog_standard",
    "normalize_theme_mode",
]
