"""Shared UI style tokens and QSS builders."""

from dataclasses import dataclass
from typing import Any

MATH_PHYS_PATTERN = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMjAiIGhl"
    "aWdodD0iMjIwIiB2aWV3Qm94PSIwIDAgMjIwIDIyMCI+CiAgPGcgZmlsbD0ibm9uZSIgc3Ry"
    "b2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDgiIHN0cm9rZS13aWR0aD0iMSI+CiAg"
    "ICA8Y2lyY2xlIGN4PSI2MCIgY3k9IjYwIiByPSIyNiIvPgogICAgPGNpcmNsZSBjeD0iMTYw"
    "IiBjeT0iMTUwIiByPSIzMiIvPgogICAgPHBhdGggZD0iTTAgMTEwIFEgMzUgODAgNzAgMTEw"
    "IFQgMTQwIDExMCBUIDIyMCAxMTAiLz4KICAgIDxwYXRoIGQ9Ik0yMCAyMDAgTCAyMDAgMjAi"
    "Lz4KICAgIDxwYXRoIGQ9Ik0zMCAyMCBMIDE5MCAxODAiLz4KICA8L2c+CiAgPGcgZmlsbD0i"
    "bm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMDYiIHN0cm9rZS13aWR0"
    "aD0iMSI+CiAgICA8cGF0aCBkPSJNMTEwIDAgTCAxMTAgMjIwIi8+CiAgICA8cGF0aCBkPSJN"
    "MCAxMTAgTCAyMjAgMTEwIi8+CiAgPC9nPgo8L3N2Zz4="
)

MATH_PHYS_BACKGROUND = f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1d2030, stop:0.5 #171a24, stop:1 #12141b);
    background-position: center;
    background-repeat: repeat;
"""

TITLEBAR_BACKGROUND = f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2b3465, stop:0.5 #1b223a, stop:0.5001 #101217, stop:1 #101217);
    background-position: top left;
    background-repeat: repeat;
"""

BASE_APP_STYLESHEET = """
    QMessageBox {
        background: #16171a;
    }
    QMessageBox QLabel {
        color: #cfcfcf;
    }
    QMessageBox QPushButton {
        background: #2a2b2f;
        color: #e6e6e6;
        border: 1px solid #3a3b40;
        padding: 6px 12px;
        border-radius: 6px;
        min-width: 90px;
    }
    QMessageBox QPushButton:hover {
        background: #34363b;
    }
    QComboBox::drop-down {
        border: none;
        width: 18px;
    }
    QComboBox QAbstractItemView {
        background: #1c1d22;
        color: #e6e6e6;
        border: 1px solid #2a2b2f;
        selection-background-color: #2f3238;
        selection-color: #f2f2f2;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 10px;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #2f3238;
        color: #f2f2f2;
    }
    QMenu {
        background: #1f2227;
        color: #e6e6e6;
        border: 1px solid #2a2b2f;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 14px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background: #2b2f36;
    }
    QMenu::separator {
        height: 1px;
        background: #2a2b2f;
        margin: 4px 8px;
    }
"""


@dataclass(frozen=True)
class ScrollbarStyleTokens:
    track: str = "#17191f"
    handle: str = "#4a5161"
    handle_hover: str = "#5c6477"
    handle_pressed: str = "#74809a"
    handle_disabled: str = "#303644"
    border: str = "#2a2d36"
    corner: str = "transparent"
    width_px: int = 12
    min_handle_px: int = 28
    radius_px: int = 6
    margin_px: int = 2


DEFAULT_SCROLLBAR_TOKENS = ScrollbarStyleTokens()


def build_scrollbar_stylesheet(tokens: ScrollbarStyleTokens = DEFAULT_SCROLLBAR_TOKENS, scope: str = "") -> str:
    prefix = f"{scope} " if scope else ""
    return f"""
{prefix}QScrollBar:vertical {{
    background: {tokens.track};
    width: {tokens.width_px}px;
    margin: {tokens.margin_px}px;
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius_px}px;
}}
{prefix}QScrollBar::handle:vertical {{
    background: {tokens.handle};
    min-height: {tokens.min_handle_px}px;
    border-radius: {tokens.radius_px}px;
}}
{prefix}QScrollBar::handle:vertical:hover {{
    background: {tokens.handle_hover};
}}
{prefix}QScrollBar::handle:vertical:pressed {{
    background: {tokens.handle_pressed};
}}
{prefix}QScrollBar::handle:vertical:disabled {{
    background: {tokens.handle_disabled};
}}
{prefix}QScrollBar::add-line:vertical,
{prefix}QScrollBar::sub-line:vertical,
{prefix}QScrollBar::add-page:vertical,
{prefix}QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
    height: 0;
}}
{prefix}QScrollBar:horizontal {{
    background: {tokens.track};
    height: {tokens.width_px}px;
    margin: {tokens.margin_px}px;
    border: 1px solid {tokens.border};
    border-radius: {tokens.radius_px}px;
}}
{prefix}QScrollBar::handle:horizontal {{
    background: {tokens.handle};
    min-width: {tokens.min_handle_px}px;
    border-radius: {tokens.radius_px}px;
}}
{prefix}QScrollBar::handle:horizontal:hover {{
    background: {tokens.handle_hover};
}}
{prefix}QScrollBar::handle:horizontal:pressed {{
    background: {tokens.handle_pressed};
}}
{prefix}QScrollBar::handle:horizontal:disabled {{
    background: {tokens.handle_disabled};
}}
{prefix}QScrollBar::add-line:horizontal,
{prefix}QScrollBar::sub-line:horizontal,
{prefix}QScrollBar::add-page:horizontal,
{prefix}QScrollBar::sub-page:horizontal {{
    background: transparent;
    border: none;
    width: 0;
}}
{prefix}QAbstractScrollArea::corner {{
    background: {tokens.corner};
}}
"""


def compose_app_stylesheet(extra_qss: str = "") -> str:
    return f"{BASE_APP_STYLESHEET}\n{extra_qss}".strip()


def apply_scrollbar_stylesheet(
    widget: Any,
    tokens: ScrollbarStyleTokens = DEFAULT_SCROLLBAR_TOKENS,
    scope: str = "",
    append: bool = True,
) -> None:
    qss = build_scrollbar_stylesheet(tokens=tokens, scope=scope)
    current = widget.styleSheet() if append and hasattr(widget, "styleSheet") else ""
    widget.setStyleSheet(f"{current}\n{qss}".strip())


APP_SCROLLBAR_STYLESHEET = build_scrollbar_stylesheet()
APP_STYLESHEET = compose_app_stylesheet(APP_SCROLLBAR_STYLESHEET)
