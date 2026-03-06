from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from mindnavigator.workspaces import projects_workspace
from mindnavigator.workspaces import tasks_workspace


def test_tasks_delegate_menu_and_checkbox_are_square_and_full_height() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = tasks_workspace.TasksItemDelegate()
    row_rect = QRect(0, 0, 980, delegate.ROW_H)
    layout = delegate._row_layout(row_rect, depth=0, has_subtasks=True)

    menu_rect = layout["menu"]
    checkbox_rect = layout["checkbox"]

    assert menu_rect.top() == row_rect.top()
    assert menu_rect.height() == row_rect.height()
    assert menu_rect.width() == row_rect.height()
    assert checkbox_rect.height() == menu_rect.height()
    assert checkbox_rect.width() == menu_rect.width()


def test_projects_delegate_has_tree_icons_and_full_height_area_quick_rect() -> None:
    _app = QApplication.instance() or QApplication([])
    delegate = projects_workspace.ProjectsItemDelegate()
    row_rect = QRect(0, 0, 980, delegate.HEADER_H)
    quick_rect = delegate._area_quick_rect(row_rect, "Area")

    assert hasattr(delegate, "_icon_tree_open")
    assert hasattr(delegate, "_icon_tree_closed")
    assert quick_rect.top() == row_rect.top()
    assert quick_rect.height() == row_rect.height()


def test_projects_workspace_uses_full_height_square_menu_rects_in_delegate() -> None:
    source = Path("mindnavigator/workspaces/projects/module_impl.py").read_text(encoding="utf-8")

    assert 'menu_rect = QRect(r.left() + left_pad, r.top(), menu_w, r.height())' in source
    assert 'menu_rect = QRect(r.right() - right_pad - menu_w, r.top(), menu_w, r.height())' in source
