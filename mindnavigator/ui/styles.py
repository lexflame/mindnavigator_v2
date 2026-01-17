"""Общие стили для фонов с абстрактным математико-физическим рисунком."""

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
    background-image: url("{MATH_PHYS_PATTERN}");
    background-position: center;
    background-repeat: repeat;
"""

TITLEBAR_BACKGROUND = f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2b3465, stop:0.5 #1b223a, stop:0.5001 #101217, stop:1 #101217);
    background-image: url("{MATH_PHYS_PATTERN}");
    background-position: top left;
    background-repeat: repeat;
"""

APP_STYLESHEET = """
    * {
        font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    }
    QMainWindow,
    QWidget {
        background: #12141b;
        color: #d9dbe0;
    }
    QLabel {
        color: #cdd0d6;
    }
    QFrame,
    QGroupBox {
        border: 1px solid #242832;
        border-radius: 8px;
    }
    QGroupBox {
        margin-top: 14px;
        padding: 12px;
        font-weight: 600;
        color: #c7cbd3;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
        color: #8f95a3;
    }
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QDateEdit,
    QTimeEdit,
    QDateTimeEdit {
        background: #171a22;
        color: #e2e6ee;
        border: 1px solid #2a2f3a;
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: #33405f;
        selection-color: #f6f7fb;
    }
    QLineEdit:focus,
    QTextEdit:focus,
    QPlainTextEdit:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus,
    QDateEdit:focus,
    QTimeEdit:focus,
    QDateTimeEdit:focus {
        border: 1px solid #3b4a6f;
        background: #1a1f2b;
    }
    QLineEdit:disabled,
    QTextEdit:disabled,
    QPlainTextEdit:disabled {
        background: #14171d;
        color: #6f7582;
        border: 1px solid #232733;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2b3550, stop:1 #1d2437);
        color: #ecf0f8;
        border: 1px solid #36435f;
        border-radius: 8px;
        padding: 6px 14px;
        min-height: 26px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #324063, stop:1 #232c43);
        border: 1px solid #425277;
    }
    QPushButton:pressed {
        background: #20283a;
        border: 1px solid #2f3b57;
    }
    QPushButton:disabled {
        background: #1a1f2a;
        color: #7a7f8b;
        border: 1px solid #252b38;
    }
    QToolButton {
        background: #1b202b;
        color: #cfd3db;
        border: 1px solid #2a2f3a;
        border-radius: 6px;
        padding: 4px 10px;
    }
    QToolButton:hover {
        background: #232a38;
        border: 1px solid #39435c;
    }
    QCheckBox,
    QRadioButton {
        spacing: 6px;
        color: #cfd3db;
    }
    QCheckBox::indicator,
    QRadioButton::indicator {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        border: 1px solid #3a4254;
        background: #151922;
    }
    QCheckBox::indicator:checked,
    QRadioButton::indicator:checked {
        background: #3b4a6f;
        border: 1px solid #4b5f8a;
    }
    QSlider::groove:horizontal {
        height: 6px;
        background: #1b1f29;
        border: 1px solid #2a2f3a;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        width: 14px;
        margin: -5px 0;
        border-radius: 7px;
        background: #3b4a6f;
        border: 1px solid #4b5f8a;
    }
    QScrollBar:vertical,
    QScrollBar:horizontal {
        background: #12141b;
        border: none;
        margin: 2px;
    }
    QScrollBar::handle:vertical,
    QScrollBar::handle:horizontal {
        background: #262c39;
        border-radius: 6px;
        min-height: 24px;
        min-width: 24px;
    }
    QScrollBar::handle:vertical:hover,
    QScrollBar::handle:horizontal:hover {
        background: #323a4d;
    }
    QScrollBar::add-line,
    QScrollBar::sub-line {
        background: none;
        border: none;
        height: 0;
        width: 0;
    }
    QTabWidget::pane {
        border: 1px solid #242832;
        border-radius: 8px;
        padding: 4px;
        background: #141824;
    }
    QTabBar::tab {
        background: #1c2130;
        color: #cdd0d6;
        border: 1px solid #2a2f3a;
        padding: 6px 12px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }
    QTabBar::tab:selected {
        background: #2a334a;
        border: 1px solid #3a4765;
        color: #f0f2f6;
    }
    QHeaderView::section {
        background: #1b202c;
        color: #cdd0d6;
        padding: 6px 10px;
        border: 1px solid #2a2f3a;
    }
    QListView,
    QTreeView,
    QTableView {
        background: #141824;
        color: #d9dbe0;
        border: 1px solid #242832;
        alternate-background-color: #161b27;
        selection-background-color: #2f3a52;
        selection-color: #f0f2f6;
        outline: none;
    }
    QToolTip {
        background: #232a38;
        color: #e7ebf2;
        border: 1px solid #3b4a6f;
        padding: 6px 10px;
        border-radius: 6px;
    }
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
