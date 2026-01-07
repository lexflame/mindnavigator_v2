from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit


class SearchNav(QWidget):
    """Панель быстрого поиска по всем сущностям приложения."""

    def __init__(self, parent=None):
        """Создает и настраивает блок быстрого поиска."""
        super().__init__(parent)
        self.setObjectName("SearchNav")
        self._ratio = 0.12
        self._min_w = 220
        self._max_w = 420

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.header = QLabel("Поиск")
        self.header.setObjectName("SearchHeader")

        self.hint = QLabel("Быстрый поиск по всем сущностям")
        self.hint.setObjectName("SearchHint")
        self.hint.setWordWrap(True)

        self.input = QLineEdit()
        self.input.setObjectName("SearchInput")
        self.input.setPlaceholderText("Проекты, задачи, заметки, файлы…")
        self.input.setClearButtonEnabled(True)

        layout.addWidget(self.header)
        layout.addWidget(self.hint)
        layout.addWidget(self.input)
        layout.addStretch(1)

        self.setStyleSheet("""
            QWidget#SearchNav {
                background: #191a1d;
                border-right: 1px solid #2a2b2f;
                border-top: 1px solid #2a2b2f;
            }
            QLabel#SearchHeader {
                color: #cfcfcf;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#SearchHint {
                color: #7a7a7a;
                font-size: 12px;
            }
            QLineEdit#SearchInput {
                background: #16171a;
                border: 1px solid #2a2b2f;
                border-radius: 4px;
                color: #cfcfcf;
                padding: 6px 8px;
            }
            QLineEdit#SearchInput:focus {
                border: 1px solid #3a3c42;
            }
        """)

    def update_width_for_window(self, window_width: int):
        """Пересчитывает ширину панели в зависимости от ширины окна."""
        w = int(window_width * self._ratio)
        w = max(self._min_w, min(self._max_w, w))
        self.setFixedWidth(w)
