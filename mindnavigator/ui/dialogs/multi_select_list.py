
from __future__ import annotations
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt


class MultiSelectList(QListWidget):
    def set_items(self, rows, id_key: str = "id", title_key: str = "title", selected_ids=None):
        selected_ids = set(selected_ids or [])
        self.clear()
        for r in rows:
            item = QListWidgetItem(str(getattr(r, title_key, None) if hasattr(r, title_key) else r[title_key]))
            rid = int(getattr(r, id_key, None) if hasattr(r, id_key) else r[id_key])
            item.setData(Qt.UserRole, rid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if rid in selected_ids else Qt.Unchecked)
            self.addItem(item)

    def selected_ids(self):
        out = []
        for i in range(self.count()):
            it = self.item(i)
            if it.checkState() == Qt.Checked:
                out.append(int(it.data(Qt.UserRole)))
        return out
