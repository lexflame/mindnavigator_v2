"""Общие стили для фонов с абстрактным математико-физическим рисунком.

Входные данные:
    Нет. Модуль содержит статические строковые шаблоны стилей.

Выходные данные:
    Строки QSS для применения к интерфейсу.
"""

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

APP_STYLESHEET = """
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
