"""ProjectsWorkspace class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .projects_model import ProjectsModel
from .projects_item_delegate import ProjectsItemDelegate
from .project_edit_dialog import ProjectEditDialog
from ._projects_list_view import _ProjectsListView
from mindnavigator.ui.styles import get_theme_palette

class ProjectsWorkspace(QWidget):
    def __init__(self, parent=None):
        """Создает рабочую область проектов."""
        super().__init__(parent)
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._theme_mode = "dark"
        self.setObjectName("ProjectsWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        top = QFrame()
        top.setObjectName("ProjectsTopbar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(10, 8, 10, 8)
        top_layout.setSpacing(8)

        self.tabs_group = QButtonGroup(self)
        self.tabs_group.setExclusive(True)

        def tab_btn(text: str) -> QToolButton:
            """Создает кнопку вкладки фильтра."""
            tab_button = QToolButton()
            tab_button.setText(text)
            tab_button.setCheckable(True)
            tab_button.setCursor(Qt.CursorShape.PointingHandCursor)
            tab_button.setAutoRaise(True)
            self.tabs_group.addButton(tab_button)
            return tab_button

        self.tab_all = tab_btn("Все")
        self.tab_active = tab_btn("Активные")
        self.tab_arch = tab_btn("Архив")
        self.tab_all.setChecked(True)

        top_layout.addWidget(self.tab_all)
        top_layout.addWidget(self.tab_active)
        top_layout.addWidget(self.tab_arch)

        top_layout.addSpacing(12)

        self.cmb_area = QComboBox()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        self.cmb_area.setFixedWidth(180)
        top_layout.addWidget(self.cmb_area)

        top_layout.addSpacing(12)

        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Любой", "Low", "Medium", "High"])
        self.cmb_priority.setFixedWidth(110)

        self.btn_create = QToolButton()
        self.btn_create.setText("Создать")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export = QToolButton()
        self.btn_export.setText("Экспорт")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import = QToolButton()
        self.btn_import.setText("Импорт")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_graph = QToolButton()
        self.btn_graph.setText("GRAPH")
        self.btn_graph.setCursor(Qt.CursorShape.PointingHandCursor)

        top_layout.addWidget(self.cmb_priority)
        top_layout.addWidget(self.btn_create)
        top_layout.addWidget(self.btn_export)
        top_layout.addWidget(self.btn_import)
        top_layout.addWidget(self.btn_graph)

        top_layout.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")
        self.search.setFixedWidth(260)
        top_layout.addWidget(self.search)

        root.addWidget(top)

        self.list = _ProjectsListView(self)
        self.list.setObjectName("ProjectsList")
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(True)
        self.list.setMouseTracking(True)
        self.list.viewport().setAcceptDrops(True)
        self.list.setDropIndicatorShown(True)
        root.addWidget(self.list, 1)

        self.model = ProjectsModel(self)
        self.list.setModel(self.model)

        self.delegate = ProjectsItemDelegate(self.list)
        self.list.setItemDelegate(self.delegate)

        for button in self.tabs_group.buttons():
            button.clicked.connect(self._on_tab_changed)

        self.search.textChanged.connect(self.model.set_search)
        self.cmb_area.currentTextChanged.connect(self._on_area_changed)
        self.cmb_priority.currentTextChanged.connect(self._on_priority_filter_changed)
        self.btn_create.clicked.connect(self._on_create_project)
        self.btn_export.clicked.connect(self._export_projects_csv)
        self.btn_import.clicked.connect(self._import_projects_csv)
        self.btn_graph.clicked.connect(self._on_graph_clicked)

        self.set_theme_mode("dark")

    def set_theme_mode(self, theme_mode: str) -> None:
        self._theme_mode = "light" if str(theme_mode).strip().lower() == "light" else "dark"
        palette = get_theme_palette(self._theme_mode)
        self.setStyleSheet(
            f"""
            QWidget#ProjectsWorkspace {{ background: {palette.window_bg}; }}

            QFrame#ProjectsTopbar {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
            }}

            QToolButton {{
                color: {palette.text};
                border: none;
                padding: 6px 8px;
            }}
            QToolButton:checked {{
                background: {palette.selection_bg};
                color: {palette.selection_text};
            }}

            QComboBox, QLineEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 6px 8px;
            }}

            QListView#ProjectsList {{
                background: {palette.window_bg};
                border: 1px solid {palette.border};
            }}
        """
        )

    def _on_tab_changed(self):
        """Обрабатывает переключение фильтров по статусу."""
        if self.tab_arch.isChecked():
            self.model.set_filter_mode("Архив")
        elif self.tab_active.isChecked():
            self.model.set_filter_mode("Активные")
        else:
            self.model.set_filter_mode("Все")

    def _on_area_changed(self, text: str):
        """Обновляет фильтрацию по области проекта."""
        if text == "Все области":
            self.model.set_area_focus(None)
        else:
            self.model.set_area_focus(text)

    def refresh_projects(self) -> None:
        """Перезагружает список проектов из базы."""
        self.model.refresh()

    def _export_projects_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Projects",
            "projects_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_projects_rows(self._db.fetch_projects())
        if not rows:
            QMessageBox.information(self, "Projects", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=PROJECTS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Projects", f"Export failed: {exc}")
            return
        QMessageBox.information(self, "Projects", "Экспорт завершен.")

    def _import_projects_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Projects",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Projects", f"Import failed: {exc}")
            return
        result = import_projects_rows(self._db, rows)
        self.refresh_projects()
        self._refresh_area_combo()
        QMessageBox.information(
            self,
            "Projects",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

    def set_task_filter(self, task_id: Optional[int]) -> None:
        """Устанавливает фильтр по задаче для списка проектов."""
        self.model.set_task_filter(task_id)

    def handle_project_drop(
        self,
        source_project_id: int,
        target_project_id: int,
        drop_after: bool,
        as_child: bool,
    ) -> bool:
        ok = self.model.move_project_by_drop(source_project_id, target_project_id, drop_after, as_child)
        if not ok:
            return False
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if index.data(ProjectRoles.ProjectId) == source_project_id:
                self.list.setCurrentIndex(index)
                break
        return True

    def focus_project(self, project_id: int) -> bool:
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            if index.data(ProjectRoles.ProjectId) != project_id:
                continue
            self.list.setCurrentIndex(index)
            self.list.scrollTo(index)
            return True
        return False

    def _refresh_area_combo(self, selected: Optional[str] = None):
        """Обновляет список областей проектов."""
        current = selected or self.cmb_area.currentText()
        self.cmb_area.blockSignals(True)
        self.cmb_area.clear()
        self.cmb_area.addItems(["Все области", *get_database().project_areas()])
        if current:
            self.cmb_area.setCurrentText(current)
        if self.cmb_area.currentText() != current and current != "Все области":
            self.cmb_area.setCurrentText("Все области")
        self.cmb_area.blockSignals(False)

    def _on_create_project(self):
        """Открывает диалог создания проекта."""
        dialog = ProjectEditDialog(parent=self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return

        values = dialog.values()
        try:
            project_id = self.model.add_project(
                area=values["area"],
                title=values["title"],
                updated=values["updated"],
                priority=values["priority"],
                archived=values["archived"],
                parent_project_id=values["parent_project_id"],
                default_task_priority=values["default_task_priority"],
                force_recurrence_kind=values["force_recurrence_kind"],
                linked_map_id=values["linked_map_id"],
                linked_note_id=values["linked_note_id"],
                linked_object_id=values["linked_object_id"],
                marker_color=values["marker_color"],
                marker_theme=values["marker_theme"],
                repository_catalog=values["repository_catalog"],
            )
            self._refresh_area_combo(values["area"])
            self.focus_project(project_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))

    def _on_priority_filter_changed(self, value: str) -> None:
        priority = None if value == "Любой" else value
        self.model.set_priority_filter(priority)

    def _on_graph_clicked(self) -> None:
        QMessageBox.information(
            self,
            "Projects",
            "Режим GRAPH запланирован как отдельный PARTITION и будет закрыт отдельным шагом.",
        )

__all__ = ["ProjectsWorkspace"]
