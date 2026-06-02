"""TaskRoles class module for tasks workspace."""

from __future__ import annotations

from PySide6.QtCore import Qt

class TaskRoles:
    RowType = Qt.ItemDataRole.UserRole + 1  # header | task
    Day = Qt.ItemDataRole.UserRole + 2
    TimeText = Qt.ItemDataRole.UserRole + 3
    Title = Qt.ItemDataRole.UserRole + 4
    Description = Qt.ItemDataRole.UserRole + 5
    Priority = Qt.ItemDataRole.UserRole + 6
    Done = Qt.ItemDataRole.UserRole + 7
    TaskId = Qt.ItemDataRole.UserRole + 8
    SortKey = Qt.ItemDataRole.UserRole + 9
    SortDirection = Qt.ItemDataRole.UserRole + 10
    DisplayTime = Qt.ItemDataRole.UserRole + 11
    ProjectTitle = Qt.ItemDataRole.UserRole + 12
    Expanded = Qt.ItemDataRole.UserRole + 13
    HasSubtasks = Qt.ItemDataRole.UserRole + 14
    SubtasksExpanded = Qt.ItemDataRole.UserRole + 15
    SubtaskDepth = Qt.ItemDataRole.UserRole + 16
    ProjectArea = Qt.ItemDataRole.UserRole + 17
    AttachmentSummary = Qt.ItemDataRole.UserRole + 18
    RecurrenceKind = Qt.ItemDataRole.UserRole + 19
    CompletionDelayMinutes = Qt.ItemDataRole.UserRole + 20
    ParentTaskId = Qt.ItemDataRole.UserRole + 21
    MarkerColor = Qt.ItemDataRole.UserRole + 22
    MarkerTheme = Qt.ItemDataRole.UserRole + 23
    BoardColumn = Qt.ItemDataRole.UserRole + 24
    IsPlanTask = Qt.ItemDataRole.UserRole + 25
    IsPlanItem = Qt.ItemDataRole.UserRole + 26
    PlanNumber = Qt.ItemDataRole.UserRole + 27
    PlanOrder = Qt.ItemDataRole.UserRole + 28
    IsCurrentPlanItem = Qt.ItemDataRole.UserRole + 29
    StartedAt = Qt.ItemDataRole.UserRole + 30
    FinishedAt = Qt.ItemDataRole.UserRole + 31
    ActualMinutes = Qt.ItemDataRole.UserRole + 32
    HeaderTotalMinutes = Qt.ItemDataRole.UserRole + 33
    HeaderOverrunMinutes = Qt.ItemDataRole.UserRole + 34
    ProjectTaskTypeId = Qt.ItemDataRole.UserRole + 35
    ProjectTaskTypeTitle = Qt.ItemDataRole.UserRole + 36
    ProjectTaskTypeColor = Qt.ItemDataRole.UserRole + 37
    ProjectTaskMetaSummary = Qt.ItemDataRole.UserRole + 38

__all__ = ["TaskRoles"]
