"""Marker type helpers and assets."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap

from .resources import resource_path


@dataclass(frozen=True)
class MarkerTypeOption:
    key: str
    label: str
    color: QColor
    asset_path: str


MARKER_TYPES: tuple[MarkerTypeOption, ...] = (
    MarkerTypeOption(
        key="blue",
        label="Рядовая метка",
        color=QColor("#4a90e2"),
        asset_path="assets/markers/marker-blue.png",
    ),
    MarkerTypeOption(
        key="green",
        label="Природный объект",
        color=QColor("#2ecc71"),
        asset_path="assets/markers/marker-green.png",
    ),
    MarkerTypeOption(
        key="orange",
        label='Объект "идея"',
        color=QColor("#f5a623"),
        asset_path="assets/markers/marker-orange.png",
    ),
    MarkerTypeOption(
        key="red",
        label="Населённый пункт",
        color=QColor("#e74c3c"),
        asset_path="assets/markers/marker-red.png",
    ),
    MarkerTypeOption(
        key="yellow",
        label="Технический объект",
        color=QColor("#f1c40f"),
        asset_path="assets/markers/marker-yellow.png",
    ),
)

DEFAULT_MARKER_TYPE_KEY = "blue"


def marker_type_options() -> list[MarkerTypeOption]:
    return list(MARKER_TYPES)


def default_marker_type() -> MarkerTypeOption:
    return marker_type_by_key(DEFAULT_MARKER_TYPE_KEY)


def marker_type_by_key(key: str) -> MarkerTypeOption:
    for option in MARKER_TYPES:
        if option.key == key:
            return option
    return MARKER_TYPES[0]


def marker_type_by_label(label: str) -> MarkerTypeOption:
    for option in MARKER_TYPES:
        if option.label == label:
            return option
    return MARKER_TYPES[0]


def marker_type_for_color(color: QColor | str) -> MarkerTypeOption:
    if isinstance(color, QColor):
        color_value = color.name().lower()
    else:
        color_value = str(color).strip().lower()
    for option in MARKER_TYPES:
        if option.color.name().lower() == color_value:
            return option
    return MARKER_TYPES[0]


def marker_type_icon(option: MarkerTypeOption) -> QIcon:
    return QIcon(resource_path(option.asset_path))


def marker_type_pixmap(option: MarkerTypeOption, size: QSize) -> QPixmap | None:
    pixmap = QPixmap(resource_path(option.asset_path))
    if pixmap.isNull():
        return None
    return pixmap.scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
