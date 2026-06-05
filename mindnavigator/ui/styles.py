"""Shared UI style tokens and runtime QSS builders."""

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


@dataclass(frozen=True)
class ThemePalette:
    mode: str
    window_bg: str
    panel_bg: str
    panel_alt_bg: str
    elevated_bg: str
    input_bg: str
    input_alt_bg: str
    border: str
    border_strong: str
    text: str
    dim_text: str
    muted_text: str
    accent: str
    accent_hover: str
    selection_bg: str
    selection_text: str
    warning: str
    danger: str
    success: str
    chip_bg: str
    chip_border: str
    chart_bg: str
    chart_grid: str
    chart_text: str
    chart_muted: str


DARK_THEME = ThemePalette(
    mode="dark",
    window_bg="#16171a",
    panel_bg="#1b1c1f",
    panel_alt_bg="#1b1c20",
    elevated_bg="#1f2227",
    input_bg="#202127",
    input_alt_bg="#131417",
    border="#2a2b2f",
    border_strong="#3a3b40",
    text="#cfcfcf",
    dim_text="#8a8a8a",
    muted_text="#6e7178",
    accent="#4f7ecf",
    accent_hover="#5a8ce0",
    selection_bg="#2f3238",
    selection_text="#f2f2f2",
    warning="#f2a23a",
    danger="#c84b4b",
    success="#4caf50",
    chip_bg="#1f2227",
    chip_border="#3a3b40",
    chart_bg="#17191f",
    chart_grid="#323641",
    chart_text="#e6e8ed",
    chart_muted="#9ea4b1",
)

LIGHT_THEME = ThemePalette(
    mode="light",
    window_bg="#f5f7fb",
    panel_bg="#eef2f8",
    panel_alt_bg="#f7f9fd",
    elevated_bg="#ffffff",
    input_bg="#ffffff",
    input_alt_bg="#f7f9fd",
    border="#cfd6e2",
    border_strong="#bbc6d6",
    text="#1f2430",
    dim_text="#566173",
    muted_text="#748094",
    accent="#3f6fd1",
    accent_hover="#315fb8",
    selection_bg="#dfe9ff",
    selection_text="#18305f",
    warning="#c67a14",
    danger="#b24a4a",
    success="#2f8f4a",
    chip_bg="#eef3fb",
    chip_border="#c8d3e3",
    chart_bg="#ffffff",
    chart_grid="#d2dae7",
    chart_text="#1f2430",
    chart_muted="#677487",
)


def normalize_theme_mode(theme_mode: str) -> str:
    return "light" if str(theme_mode).strip().lower() == "light" else "dark"


def get_theme_palette(theme_mode: str) -> ThemePalette:
    return LIGHT_THEME if normalize_theme_mode(theme_mode) == "light" else DARK_THEME


@dataclass(frozen=True)
class ScrollbarStyleTokens:
    track: str
    handle: str
    handle_hover: str
    handle_pressed: str
    handle_disabled: str
    border: str
    corner: str = "transparent"
    width_px: int = 12
    min_handle_px: int = 28
    radius_px: int = 6
    margin_px: int = 2


DEFAULT_SCROLLBAR_TOKENS = ScrollbarStyleTokens(
    track="#17191f",
    handle="#4a5161",
    handle_hover="#5c6477",
    handle_pressed="#74809a",
    handle_disabled="#303644",
    border="#2a2d36",
)

LIGHT_SCROLLBAR_TOKENS = ScrollbarStyleTokens(
    track="#e7ecf5",
    handle="#9ba8bd",
    handle_hover="#8795ad",
    handle_pressed="#74839d",
    handle_disabled="#c4ccd8",
    border="#c9d2df",
)


def get_scrollbar_tokens(theme_mode: str) -> ScrollbarStyleTokens:
    return LIGHT_SCROLLBAR_TOKENS if normalize_theme_mode(theme_mode) == "light" else DEFAULT_SCROLLBAR_TOKENS


def build_scrollbar_stylesheet(tokens: ScrollbarStyleTokens, scope: str = "") -> str:
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


def build_popup_menu_stylesheet(theme_mode: str) -> str:
    palette = get_theme_palette(theme_mode)
    return f"""
QMenu {{
    background: {palette.elevated_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 14px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {palette.selection_bg};
    color: {palette.selection_text};
}}
QMenu::separator {{
    height: 1px;
    background: {palette.border};
    margin: 4px 8px;
}}
""".strip()


def build_calendar_popup_stylesheet(theme_mode: str) -> str:
    palette = get_theme_palette(theme_mode)
    return f"""
QCalendarWidget {{
    background: {palette.panel_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: {palette.input_alt_bg};
    border-bottom: 1px solid {palette.border};
}}
QCalendarWidget QToolButton {{
    background: transparent;
    color: {palette.text};
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    margin: 2px;
}}
QCalendarWidget QToolButton:hover {{
    background: {palette.elevated_bg};
    color: {palette.accent_hover};
}}
QCalendarWidget QToolButton:pressed {{
    background: {palette.selection_bg};
    color: {palette.selection_text};
}}
QCalendarWidget QSpinBox {{
    background: {palette.elevated_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
    border-radius: 5px;
    padding: 2px 6px;
}}
QCalendarWidget QMenu {{
    background: {palette.elevated_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
}}
QCalendarWidget QMenu::item:selected {{
    background: {palette.selection_bg};
    color: {palette.selection_text};
}}
QCalendarWidget QAbstractItemView {{
    background: {palette.panel_bg};
    alternate-background-color: {palette.panel_alt_bg};
    color: {palette.text};
    selection-background-color: {palette.accent};
    selection-color: {palette.selection_text};
    outline: none;
}}
QCalendarWidget QAbstractItemView:enabled {{
    color: {palette.text};
}}
QCalendarWidget QAbstractItemView:disabled {{
    color: {palette.muted_text};
}}
""".strip()


def build_base_app_stylesheet(theme_mode: str) -> str:
    palette = get_theme_palette(theme_mode)
    return f"""
QMessageBox {{
    background: {palette.window_bg};
}}
QMessageBox QLabel {{
    color: {palette.text};
}}
QMessageBox QPushButton {{
    background: {palette.panel_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
    padding: 6px 12px;
    border-radius: 6px;
    min-width: 90px;
}}
QMessageBox QPushButton:hover {{
    background: {palette.selection_bg};
    color: {palette.selection_text};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background: {palette.elevated_bg};
    color: {palette.text};
    border: 1px solid {palette.border};
    selection-background-color: {palette.selection_bg};
    selection-color: {palette.selection_text};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
}}
QComboBox QAbstractItemView::item:selected {{
    background: {palette.selection_bg};
    color: {palette.selection_text};
}}
{build_popup_menu_stylesheet(theme_mode)}
""".strip()


def compose_app_stylesheet(theme_mode: str, extra_qss: str = "") -> str:
    base = build_base_app_stylesheet(theme_mode)
    return f"{base}\n{extra_qss}".strip()


def build_app_stylesheet(theme_mode: str) -> str:
    scrollbar_qss = build_scrollbar_stylesheet(get_scrollbar_tokens(theme_mode))
    return compose_app_stylesheet(theme_mode, scrollbar_qss)


def apply_scrollbar_stylesheet(
    widget: Any,
    tokens: ScrollbarStyleTokens | None = None,
    scope: str = "",
    append: bool = True,
) -> None:
    resolved_tokens = tokens or DEFAULT_SCROLLBAR_TOKENS
    qss = build_scrollbar_stylesheet(tokens=resolved_tokens, scope=scope)
    current = widget.styleSheet() if append and hasattr(widget, "styleSheet") else ""
    widget.setStyleSheet(f"{current}\n{qss}".strip())


APP_SCROLLBAR_STYLESHEET = build_scrollbar_stylesheet(DEFAULT_SCROLLBAR_TOKENS)
APP_STYLESHEET = build_app_stylesheet("dark")
