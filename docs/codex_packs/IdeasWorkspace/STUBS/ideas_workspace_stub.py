"""IdeasWorkspace stub.

Wires UI pieces together. Replace imports with real project paths.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLineEdit, QToolButton,
    QListView, QTabWidget, QLabel, QFrame
)

# TODO: replace with your actual BaseWorkspace import
# from mindnavigator.workspaces.base_workspace import BaseWorkspace
from .ideas_controller_stub import IdeasController
from .ideas_list_model_stub import IdeasListModel
from .ideas_item_delegate_stub import IdeasItemDelegate


class BaseWorkspace(QWidget):  # placeholder: remove
    def __init__(self, *args, **kwargs):
        super().__init__()


class IdeasWorkspace(BaseWorkspace):
    def __init__(self, controller: IdeasController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._selected_id: Optional[str] = None

        self._build_ui()
        self._bind_signals()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # TopBar
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Поиск по идеям')

        self.btn_new = QToolButton()
        self.btn_new.setText('+ Идея')
        self.btn_import = QToolButton()
        self.btn_import.setText('Импорт')
        self.btn_triage = QToolButton()
        self.btn_triage.setText('Разобрать')
        self.btn_archive = QToolButton()
        self.btn_archive.setText('В архив')

        top.addWidget(self.search, 1)
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_import)
        top.addWidget(self.btn_triage)
        top.addWidget(self.btn_archive)
        root.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # Left list
        left = QFrame()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)

        self.list_view = QListView()
        self.list_view.setUniformItemSizes(False)
        self.model = IdeasListModel([])
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(IdeasItemDelegate())
        left_l.addWidget(self.list_view, 1)

        # Right inspector
        right = QFrame()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tab_content = QLabel('Content editor goes here')
        self.tab_relations = QLabel('Relations go here')
        self.tab_materials = QLabel('Materials go here')
        self.tab_decision = QLabel('Transform actions go here')

        self.tabs.addTab(self.tab_content, 'Содержание')
        self.tabs.addTab(self.tab_relations, 'Связи')
        self.tabs.addTab(self.tab_materials, 'Материалы')
        self.tabs.addTab(self.tab_decision, 'Решение')
        right_l.addWidget(self.tabs, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    def _bind_signals(self):
        self.search.textChanged.connect(self.apply_filters)
        self.list_view.clicked.connect(self._on_select)

        self.btn_new.clicked.connect(self._on_new)
        self.btn_archive.clicked.connect(self._on_archive)

    def refresh(self):
        ideas = self.controller.list(search=self.search.text() or None, archived=False)
        self.model.set_ideas(ideas)

    def apply_filters(self):
        self.refresh()

    def _on_select(self, index):
        idea_id = index.data(IdeasListModel.ROLE_ID)
        self._selected_id = idea_id
        # TODO: load idea and populate inspector

    def _on_new(self):
        # TODO: open create dialog or create empty idea and focus title
        pass

    def _on_archive(self):
        if not self._selected_id:
            return
        # TODO: archive selected with confirm
        pass
