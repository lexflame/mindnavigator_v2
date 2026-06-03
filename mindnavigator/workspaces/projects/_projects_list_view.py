"""_ProjectsListView class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .projects_workspace import ProjectsWorkspace

class _ProjectsListView(QListView):
    def __init__(self, owner: "ProjectsWorkspace"):
        super().__init__(owner)
        self._owner = owner
        self._drag_source_project_id: Optional[int] = None
        self._pressed_project_id: Optional[int] = None

    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        row_type = index.data(ProjectRoles.RowType) if index.isValid() else None
        project_id = index.data(ProjectRoles.ProjectId) if row_type == "project" else None
        self._pressed_project_id = project_id if isinstance(project_id, int) else None
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            index = self.indexAt(point)
            if index.isValid() and index.data(ProjectRoles.RowType) == "project":
                delegate = self.itemDelegate()
                folder_rect = getattr(delegate, "project_folder_rect", None)
                open_project_editor = getattr(delegate, "open_project_editor", None)
                if callable(folder_rect) and callable(open_project_editor):
                    rect = folder_rect(self.visualRect(index))
                    if rect.contains(point):
                        open_project_editor(index)
                        event.accept()
                        return
        super().mouseDoubleClickEvent(event)

    def startDrag(self, supported_actions):
        if isinstance(self._pressed_project_id, int):
            self._drag_source_project_id = self._pressed_project_id
        else:
            index = self.currentIndex()
            row_type = index.data(ProjectRoles.RowType)
            project_id = index.data(ProjectRoles.ProjectId) if row_type == "project" else None
            self._drag_source_project_id = project_id if isinstance(project_id, int) else None
        super().startDrag(supported_actions)
        self._pressed_project_id = None

    def dropEvent(self, event):
        source_id = self._drag_source_project_id
        if not isinstance(source_id, int):
            event.ignore()
            return

        point = event.position().toPoint()
        target_index = self.indexAt(point)
        if not target_index.isValid() or target_index.data(ProjectRoles.RowType) != "project":
            event.ignore()
            self._drag_source_project_id = None
            return

        target_id = target_index.data(ProjectRoles.ProjectId)
        if not isinstance(target_id, int):
            event.ignore()
            self._drag_source_project_id = None
            return

        rect = self.visualRect(target_index)
        margin = max(4, rect.height() // 4)
        drop_before_zone = point.y() <= rect.top() + margin
        drop_after_zone = point.y() >= rect.bottom() - margin
        drop_after = point.y() > rect.center().y()
        as_child = not drop_before_zone and not drop_after_zone

        if target_id == source_id:
            direction = 1 if drop_after else -1
            row = target_index.row() + direction
            fallback_id = None
            while 0 <= row < self.model().rowCount():
                idx = self.model().index(row, 0)
                if idx.data(ProjectRoles.RowType) == "project":
                    maybe_id = idx.data(ProjectRoles.ProjectId)
                    if isinstance(maybe_id, int) and maybe_id != source_id:
                        fallback_id = maybe_id
                        break
                row += direction
            if fallback_id is None:
                event.ignore()
                self._drag_source_project_id = None
                return
            target_id = fallback_id
            as_child = False

        ok = self._owner.handle_project_drop(source_id, target_id, drop_after, as_child)
        if ok:
            event.acceptProposedAction()
        else:
            event.ignore()
        self._drag_source_project_id = None

__all__ = ["_ProjectsListView"]
