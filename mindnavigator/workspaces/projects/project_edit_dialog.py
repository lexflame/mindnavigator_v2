"""ProjectEditDialog class module for projects workspace."""

from __future__ import annotations

import json
from html import escape

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QPlainTextEdit,
)

from ._shared import *  # noqa: F401,F403
from mindnavigator.ui.editable_list import EditableListItem, EditableListWidget
from mindnavigator.ui.filterable_combobox import FilterableComboBox
from mindnavigator.ui.styles import get_theme_palette

PROJECT_REFLECT_SETTING_PREFIX = "project_reflect_in_tasks"
PROJECT_REFLECT_REPOSITORY_CATALOG = "repository_catalog"
PROJECT_REFLECT_REPOSITORY_LINKS = "repository_links"
PROJECT_REFLECT_WIKI_LINKS = "wiki_links"
PROJECT_REFLECT_LINKED_MAP = "linked_map"
PROJECT_REFLECT_LINKED_NOTE = "linked_note"
PROJECT_REFLECT_LINKED_OBJECT = "linked_object"
PROJECT_REFLECT_KEYS = {
    PROJECT_REFLECT_REPOSITORY_CATALOG,
    PROJECT_REFLECT_REPOSITORY_LINKS,
    PROJECT_REFLECT_WIKI_LINKS,
    PROJECT_REFLECT_LINKED_MAP,
    PROJECT_REFLECT_LINKED_NOTE,
    PROJECT_REFLECT_LINKED_OBJECT,
}


class _CurrentPageStackedWidget(QStackedWidget):
    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        current = self.currentWidget()
        return current.minimumSizeHint() if current is not None else super().minimumSizeHint()


class ProjectEditDialog(QDialog):
    def __init__(self, project: Optional[ProjectRow] = None, parent=None):
        """Создает диалог создания или редактирования проекта."""
        super().__init__(parent)
        is_new = project is None
        self._project = project
        self._db = get_database()
        self._edit_mode = is_new
        self._palette = get_theme_palette("dark")
        self._preview_fields: list[tuple[QStackedWidget, QLabel, QWidget, object]] = []
        self.setWindowTitle("Создание проекта" if is_new else "Редактирование проекта")
        self.setObjectName("ProjectEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.resize(1380, 900)
        self.setMinimumSize(1180, 760)

        self.area_edit = FilterableComboBox(max_visible_items=10)
        self.area_edit.addItems(self._db.project_areas())
        self.area_edit.setCurrentIndex(-1)
        self.area_edit.setEditText(project.area if project else "")
        if self.area_edit.lineEdit() is not None:
            self.area_edit.lineEdit().setPlaceholderText("Область проекта")

        self.title_edit = QLineEdit(project.title if project else "")
        self.title_edit.setPlaceholderText("Название проекта")

        self.updated_edit = QDateEdit()
        self.updated_edit.setCalendarPopup(True)
        self.updated_edit.setDisplayFormat("dd.MM.yyyy")
        self.updated_edit.setKeyboardTracking(False)
        self.updated_edit.setDate(QDate.currentDate())
        self.display_properties_edit = self._make_multiline_edit("WIKI | https://docs.example.com | name_link")
        display_properties_row = self._make_inline_property_editor(
            self.display_properties_edit,
            "display_properties",
            self._add_display_property_line,
        )
        if project:
            self.updated_edit.setDate(QDate(project.updated.year, project.updated.month, project.updated.day))

        self.priority_edit = QComboBox()
        self.priority_edit.addItems(["Low", "Medium", "High"])
        self.priority_edit.setCurrentText(project.priority if project else "Medium")
        self.parent_project_edit = QComboBox()
        self.parent_project_edit.addItem("None", None)
        for item in self._db.fetch_projects():
            if project and item.id == project.id:
                continue
            self.parent_project_edit.addItem(f"{item.area} / {item.title}", item.id)
        parent_idx = self.parent_project_edit.findData(project.parent_project_id if project else None)
        if parent_idx >= 0:
            self.parent_project_edit.setCurrentIndex(parent_idx)

        self.default_task_priority_edit = QComboBox()
        self.default_task_priority_edit.addItem("None", "")
        self.default_task_priority_edit.addItem("High", "High")
        self.default_task_priority_edit.addItem("Medium", "Medium")
        self.default_task_priority_edit.addItem("Low", "Low")
        default_priority = (project.default_task_priority if project else "") or ""
        default_prio_idx = self.default_task_priority_edit.findData(default_priority)
        if default_prio_idx >= 0:
            self.default_task_priority_edit.setCurrentIndex(default_prio_idx)

        self.force_recurrence_kind_edit = QComboBox()
        self.force_recurrence_kind_edit.addItem("None", "")
        self.force_recurrence_kind_edit.addItem("Daily", "daily")
        self.force_recurrence_kind_edit.addItem("Weekly", "weekly")
        self.force_recurrence_kind_edit.addItem("Monthly", "monthly")
        recurrence_idx = self.force_recurrence_kind_edit.findData((project.force_recurrence_kind if project else "") or "")
        if recurrence_idx >= 0:
            self.force_recurrence_kind_edit.setCurrentIndex(recurrence_idx)

        self.linked_map_edit = QComboBox()
        self.linked_map_edit.addItem("None", None)
        for map_item in self._db.fetch_maps():
            self.linked_map_edit.addItem(map_item.title, map_item.id)
        linked_map_idx = self.linked_map_edit.findData(project.linked_map_id if project else None)
        if linked_map_idx >= 0:
            self.linked_map_edit.setCurrentIndex(linked_map_idx)

        self.linked_note_edit = QComboBox()
        self.linked_note_edit.addItem("None", None)
        for note_item in self._db.fetch_notes():
            self.linked_note_edit.addItem(note_item.title, note_item.id)
        linked_note_idx = self.linked_note_edit.findData(project.linked_note_id if project else None)
        if linked_note_idx >= 0:
            self.linked_note_edit.setCurrentIndex(linked_note_idx)

        self.linked_object_edit = QComboBox()
        self.linked_object_edit.addItem("None", None)
        for object_item in self._db.fetch_objects():
            self.linked_object_edit.addItem(object_item.title, object_item.id)
        linked_object_idx = self.linked_object_edit.findData(project.linked_object_id if project else None)
        if linked_object_idx >= 0:
            self.linked_object_edit.setCurrentIndex(linked_object_idx)

        self.marker_color_edit = QComboBox()
        self.marker_color_edit.addItem("None", "")
        self.marker_color_edit.addItem("Blue", "#4C78D0")
        self.marker_color_edit.addItem("Green", "#3FAF72")
        self.marker_color_edit.addItem("Orange", "#D68A3A")
        self.marker_color_edit.addItem("Red", "#C95656")
        self.marker_color_edit.addItem("Purple", "#8A63D2")
        marker_color_idx = self.marker_color_edit.findData((project.marker_color if project else "") or "")
        if marker_color_idx >= 0:
            self.marker_color_edit.setCurrentIndex(marker_color_idx)

        self.marker_theme_edit = QComboBox()
        self.marker_theme_edit.addItem("None", "")
        self.marker_theme_edit.addItem("Movies", "movies")
        self.marker_theme_edit.addItem("Games", "games")
        self.marker_theme_edit.addItem("Books", "books")
        self.marker_theme_edit.addItem("Music", "music")
        self.marker_theme_edit.addItem("Work", "work")
        self.marker_theme_edit.addItem("Personal", "personal")
        self.marker_theme_edit.addItem("Dev", "dev")
        marker_theme_idx = self.marker_theme_edit.findData((project.marker_theme if project else "") or "")
        if marker_theme_idx >= 0:
            self.marker_theme_edit.setCurrentIndex(marker_theme_idx)

        self.repository_catalog_edit = QLineEdit((project.repository_catalog if project else "") or "")
        self.repository_catalog_edit.setPlaceholderText("Путь к локальному репозиторию")
        self.repository_catalog_row = self._make_repository_catalog_editor()
        self.reflect_repository_catalog_edit = self._make_reflect_checkbox()
        self.reflect_repository_links_edit = self._make_reflect_checkbox()
        self.reflect_wiki_links_edit = self._make_reflect_checkbox()
        self.reflect_linked_map_edit = self._make_reflect_checkbox()
        self.reflect_linked_note_edit = self._make_reflect_checkbox()
        self.reflect_linked_object_edit = self._make_reflect_checkbox()

        self.archived_edit = QCheckBox("Архивировать")
        self.archived_edit.setChecked(project.archived if project else False)

        self.task_types_edit = self._make_multiline_edit(
            "DEV | #4C78D0 | dev | active\nMUSIC | #8A63D2 | music | active"
        )
        self.related_projects_edit = self._make_multiline_edit("ID связанных проектов, по одному в строке")
        self.related_tasks_edit = self._make_multiline_edit("ID связанных задач, по одному в строке")
        self.repository_links_edit = self._make_multiline_edit("MindNavigator Core | D:/_Branch/PROJECTS/mindnavigator")
        self.wiki_links_edit = self._make_multiline_edit("Project Wiki | https://docs.example.com/project")
        self.display_properties_edit.setPlaceholderText("WIKI | https://docs.example.com | name_link")
        task_types_row = self._make_inline_property_editor(
            self.task_types_edit,
            "task_types",
            self._add_task_type_line,
        )
        related_projects_row = self._make_inline_property_editor(
            self.related_projects_edit,
            "related_projects",
            self._add_related_project_line,
        )
        related_tasks_row = self._make_inline_property_editor(
            self.related_tasks_edit,
            "related_tasks",
            self._add_related_task_line,
        )
        repository_links_row = self._make_inline_property_editor(
            self.repository_links_edit,
            "repository_links",
            self._add_repository_link_line,
        )
        wiki_links_row = self._make_inline_property_editor(
            self.wiki_links_edit,
            "wiki_links",
            self._add_wiki_link_line,
        )
        if project:
            self._load_project_properties(project.id)
            self._load_project_reflect_settings(project.id)
        self._refresh_inline_property_lists()

        self._editor_controls = [
            self.area_edit,
            self.title_edit,
            self.updated_edit,
            self.priority_edit,
            self.parent_project_edit,
            self.default_task_priority_edit,
            self.force_recurrence_kind_edit,
            self.linked_map_edit,
            self.linked_note_edit,
            self.linked_object_edit,
            self.marker_color_edit,
            self.marker_theme_edit,
            self.repository_catalog_edit,
            self.reflect_repository_catalog_edit,
            self.reflect_repository_links_edit,
            self.reflect_wiki_links_edit,
            self.reflect_linked_map_edit,
            self.reflect_linked_note_edit,
            self.reflect_linked_object_edit,
            self.archived_edit,
            self.task_types_edit,
            self.related_projects_edit,
            self.related_tasks_edit,
            self.repository_links_edit,
            self.wiki_links_edit,
            self.display_properties_edit,
        ]
        self._edit_action_buttons: list[QWidget] = []
        for row in (task_types_row, related_projects_row, related_tasks_row, repository_links_row, wiki_links_row, display_properties_row):
            self._edit_action_buttons.extend(row.findChildren(QToolButton))
        self.add_relation_button = QToolButton()
        self.add_relation_button.setText("+ Добавить связь")
        self.add_relation_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_relation_button.clicked.connect(self._add_relation_dialog)
        self._edit_action_buttons.append(self.add_relation_button)
        area_field = self._field_stack(self.area_edit, lambda: self.area_edit.currentText().strip() or "Не задано")
        updated_field = self._field_stack(self.updated_edit, lambda: self.updated_edit.date().toString("dd.MM.yyyy"))
        priority_field = self._field_stack(self.priority_edit, lambda: self.priority_edit.currentText().strip() or "Medium")
        parent_field = self._field_stack(self.parent_project_edit, lambda: self.parent_project_edit.currentText().strip() or "None")
        title_field = self._field_stack(self.title_edit, lambda: self.title_edit.text().strip() or "Не задано")
        repository_catalog_field = self._field_stack(
            self._make_reflectable_editor(self.repository_catalog_row, self.reflect_repository_catalog_edit),
            lambda: self.repository_catalog_edit.text().strip() or "Путь к локальному репозиторию не указан",
        )
        repository_links_field = self._field_stack(
            self._make_reflectable_editor(repository_links_row, self.reflect_repository_links_edit),
            lambda: self._chip_preview(self.repository_links_edit.toPlainText(), "Репозитории не указаны"),
            rich=True,
        )
        wiki_links_field = self._field_stack(
            self._make_reflectable_editor(wiki_links_row, self.reflect_wiki_links_edit),
            lambda: self._chip_preview(self.wiki_links_edit.toPlainText(), "Wiki не указана"),
            rich=True,
        )
        related_projects_field = self._field_stack(
            related_projects_row,
            lambda: self._chip_preview(self.related_projects_edit.toPlainText(), "Нет связанных проектов"),
            rich=True,
        )
        related_tasks_field = self._field_stack(
            related_tasks_row,
            lambda: self._chip_preview(self.related_tasks_edit.toPlainText(), "Нет связанных задач"),
            rich=True,
        )
        task_types_field = self._field_stack(
            task_types_row,
            lambda: self._task_types_preview(),
            rich=True,
        )
        display_properties_field = self._field_stack(
            display_properties_row,
            lambda: self._display_properties_preview(),
            rich=True,
        )
        linked_map_field = self._field_stack(
            self._make_reflectable_editor(self.linked_map_edit, self.reflect_linked_map_edit),
            lambda: self.linked_map_edit.currentText().strip() or "None",
        )
        linked_note_field = self._field_stack(
            self._make_reflectable_editor(self.linked_note_edit, self.reflect_linked_note_edit),
            lambda: self.linked_note_edit.currentText().strip() or "None",
        )
        linked_object_field = self._field_stack(
            self._make_reflectable_editor(self.linked_object_edit, self.reflect_linked_object_edit),
            lambda: self.linked_object_edit.currentText().strip() or "None",
        )
        default_priority_field = self._field_stack(
            self.default_task_priority_edit,
            lambda: self.default_task_priority_edit.currentText().strip() or "None",
        )
        recurrence_field = self._field_stack(
            self.force_recurrence_kind_edit,
            lambda: self.force_recurrence_kind_edit.currentText().strip() or "None",
        )
        marker_color_field = self._field_stack(self.marker_color_edit, lambda: self.marker_color_edit.currentText().strip() or "None")
        marker_theme_field = self._field_stack(self.marker_theme_edit, lambda: self.marker_theme_edit.currentText().strip() or "None")
        archived_field = self._field_stack(self.archived_edit, lambda: "Да" if self.archived_edit.isChecked() else "Нет")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(0)

        self.shell = QFrame(self)
        self.shell.setObjectName("ProjectDialogShell")
        root.addWidget(self.shell, 1)
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(20, 16, 20, 12)
        shell_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(4)
        self.title_label = QLabel(project.title if project else "Новый проект")
        self.title_label.setObjectName("DialogTitle")
        self.mode_label = QLabel("Редактирование проекта" if is_new else "Просмотр проекта")
        self.mode_label.setObjectName("ProjectDialogMode")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.mode_label)
        header_row.addLayout(title_box, 1)
        self.close_button = QPushButton("Закрыть")
        self.close_button.setObjectName("ProjectDialogSecondaryButton")
        self.edit_button = QPushButton("Редактировать")
        self.edit_button.setObjectName("ProjectDialogPrimaryButton")
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("ProjectDialogPrimaryButton")
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setObjectName("ProjectDialogSecondaryButton")
        self.close_button.clicked.connect(self.reject)
        self.edit_button.clicked.connect(lambda: self._set_edit_mode(True))
        self.save_button.clicked.connect(self._on_accept)
        self.cancel_button.clicked.connect(self.reject)
        header_row.addWidget(self.close_button)
        header_row.addWidget(self.edit_button)
        header_row.addWidget(self.cancel_button)
        header_row.addWidget(self.save_button)
        shell_layout.addLayout(header_row)

        metrics_grid = QGridLayout()
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        metrics_grid.setHorizontalSpacing(10)
        metrics_grid.setVerticalSpacing(10)
        metrics_grid.addWidget(self._metric_card("Область", area_field), 0, 0)
        metrics_grid.addWidget(self._metric_card("Дата обновления", updated_field), 0, 1)
        metrics_grid.addWidget(self._metric_card("Приоритет", priority_field), 0, 2)
        metrics_grid.addWidget(self._metric_card("Родительский проект", parent_field), 0, 3)
        shell_layout.addLayout(metrics_grid)

        scroll = QScrollArea(self.shell)
        scroll.setObjectName("ProjectDialogScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("ProjectDialogContent")
        scroll.setWidget(content)
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self._content_widget = content
        self._content_layout = content_layout

        main_card = self._section_card("Основное")
        main_form = self._section_form(main_card)
        main_form.addRow("Название", title_field)
        main_form.addRow("Каталог репозитория", repository_catalog_field)
        main_form.addRow("Репозитории", repository_links_field)
        main_form.addRow("Wiki", wiki_links_field)

        links_card = self._section_card("Связи")
        links_form = self._section_form(links_card)
        links_form.addRow("Связанные проекты", related_projects_field)
        links_form.addRow("Связанные задачи", related_tasks_field)
        links_form.addRow("Связанная карта", linked_map_field)
        links_form.addRow("Связанная заметка", linked_note_field)
        links_form.addRow("Связанный объект", linked_object_field)
        links_form.addRow("", self.add_relation_button)

        types_card = self._section_card("Типы задач")
        types_form = self._section_form(types_card)
        types_form.addRow("", task_types_field)

        display_properties_card = self._section_card("Отображаемые свойства")
        display_properties_form = self._section_form(display_properties_card)
        display_properties_form.addRow("", display_properties_field)

        properties_card = self._section_card("Свойства")
        properties_form = self._section_form(properties_card)
        properties_form.addRow("Приоритет задач по умолчанию", default_priority_field)
        properties_form.addRow("Принудительное повторение", recurrence_field)
        properties_form.addRow("Маркер (цвет)", marker_color_field)
        properties_form.addRow("Тема маркера", marker_theme_field)
        properties_form.addRow("Архивирован", archived_field)

        hierarchy_card = self._section_card("Иерархия и правила")
        hierarchy_form = self._section_form(hierarchy_card)
        hierarchy_form.addRow("Родительский проект", QLabel(self.parent_project_edit.currentText()))
        preset_note = QLabel("Настройки поведения задач, повторяемости, напоминаний и другие правила наследуются из родительского проекта или глобальных параметров системы.")
        preset_note.setObjectName("ProjectDialogInfo")
        preset_note.setWordWrap(True)
        hierarchy_form.addRow("Поведение задач по умолчанию", QLabel("Preset не задан"))
        hierarchy_form.addRow("", preset_note)

        stats_card = self._section_card("Статистика")
        stats_layout = stats_card.layout()
        if isinstance(stats_layout, QVBoxLayout):
            stats_layout.addLayout(self._statistics_row())

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(10)
        left_column.addWidget(main_card)
        left_column.addWidget(types_card)

        center_column = QVBoxLayout()
        center_column.setContentsMargins(0, 0, 0, 0)
        center_column.setSpacing(10)
        center_column.addWidget(properties_card)
        center_column.addWidget(hierarchy_card)
        center_column.addWidget(stats_card)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(10)
        right_column.addWidget(links_card)
        right_column.addWidget(display_properties_card)

        self._content_columns = (left_column, center_column, right_column)
        self._content_card_columns = (
            (main_card, types_card),
            (properties_card, hierarchy_card, stats_card),
            (links_card, display_properties_card),
        )
        content_layout.addLayout(left_column, 1)
        content_layout.addLayout(center_column, 1)
        content_layout.addLayout(right_column, 1)
        shell_layout.addWidget(scroll, 1)

        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: self._set_edit_mode(True))
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_shortcut)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_accept)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_accept)

        palette = self._palette
        self.setStyleSheet(f"""
            QDialog#ProjectEditDialog {{
                background: {palette.window_bg};
            }}

            QFrame#ProjectDialogShell {{
                background: {palette.panel_bg};
                border: 1px solid {palette.border};
                border-radius: 14px;
            }}

            QDialog#ProjectEditDialog QLabel {{
                color: {palette.text};
            }}

            QDialog#ProjectEditDialog QLabel#DialogTitle {{
                color: {palette.selection_text};
                font-size: 26px;
                font-weight: 600;
            }}

            QLabel#ProjectDialogMode {{
                color: {palette.dim_text};
                font-size: 14px;
            }}

            QFrame#ProjectDialogMetric,
            QFrame#ProjectDialogSection {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 8px;
            }}

            QLabel#ProjectDialogSectionTitle {{
                color: {palette.selection_text};
                font-size: 16px;
                font-weight: 600;
            }}

            QLabel#ProjectDialogMetricTitle {{
                color: {palette.dim_text};
                font-size: 12px;
            }}

            QLabel#ProjectDialogInfo {{
                color: {palette.text};
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 7px;
                padding: 9px 11px;
            }}

            QLabel#ProjectDialogValue {{
                color: {palette.text};
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 28px;
            }}

            QScrollArea#ProjectDialogScroll {{
                background: transparent;
                border: none;
            }}

            QWidget#ProjectDialogContent {{
                background: transparent;
            }}

            QDialog#ProjectEditDialog QLineEdit,
            QDialog#ProjectEditDialog QComboBox,
            QDialog#ProjectEditDialog QDateEdit,
            QDialog#ProjectEditDialog QPlainTextEdit {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                padding: 7px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectEditDialog QLineEdit:disabled,
            QDialog#ProjectEditDialog QComboBox:disabled,
            QDialog#ProjectEditDialog QDateEdit:disabled,
            QDialog#ProjectEditDialog QPlainTextEdit:disabled {{
                color: {palette.text};
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
            }}

            QDialog#ProjectEditDialog QCheckBox {{
                color: {palette.text};
                padding: 4px 0;
            }}

            QDialog#ProjectEditDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#ProjectEditDialog QPushButton,
            QDialog#ProjectEditDialog QToolButton {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectEditDialog QPushButton:hover,
            QDialog#ProjectEditDialog QToolButton:hover {{
                background: {palette.selection_bg};
            }}

            QPushButton#ProjectDialogPrimaryButton {{
                background: {palette.accent};
                border: 1px solid {palette.accent_hover};
                color: {palette.selection_text};
                font-weight: 600;
                min-width: 132px;
            }}

            QPushButton#ProjectDialogSecondaryButton {{
                min-width: 118px;
            }}

            QToolButton#ProjectDialogIconButton {{
                min-width: 32px;
                max-width: 36px;
                padding: 8px 0;
            }}

            QFrame#EditableList {{
                background: transparent;
                border: none;
            }}

            QFrame#EditableListRow {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 7px;
            }}

            QLabel#EditableListEmpty {{
                color: {palette.dim_text};
                background: {palette.input_alt_bg};
                border: 1px dashed {palette.border};
                border-radius: 7px;
                padding: 9px 11px;
            }}

            QLabel#EditableListDetail {{
                color: {palette.dim_text};
                padding: 0 4px;
            }}

            QLineEdit#EditableListValue {{
                background: transparent;
                border: none;
                color: {palette.text};
                padding: 7px 8px;
            }}

            QDialog#ProjectEditDialog QToolButton#EditableListIconButton {{
                min-width: 30px;
                max-width: 30px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
                border-radius: 6px;
            }}
        """)
        self._set_edit_mode(self._edit_mode)

    def _field_stack(self, editor: QWidget, value_getter: object, rich: bool = False) -> QStackedWidget:
        stack = _CurrentPageStackedWidget()
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label = QLabel()
        label.setObjectName("ProjectDialogValue")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if rich:
            label.setTextFormat(Qt.TextFormat.RichText)
        stack.addWidget(label)
        stack.addWidget(editor)
        label.installEventFilter(self)
        self._preview_fields.append((stack, label, editor, value_getter))
        return stack

    def _refresh_preview_fields(self) -> None:
        for stack, label, _editor, value_getter in self._preview_fields:
            value = value_getter() if callable(value_getter) else ""
            label.setText(str(value))
            stack.setCurrentIndex(1 if self._edit_mode else 0)
            stack.updateGeometry()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if event.type() != QEvent.Type.MouseButtonDblClick:
            return super().eventFilter(watched, event)
        for _stack, label, editor, _value_getter in self._preview_fields:
            if watched is not label:
                continue
            self._set_edit_mode(True)
            self._focus_editor(editor)
            return True
        return super().eventFilter(watched, event)

    def _focus_editor(self, editor: QWidget) -> None:
        if isinstance(editor, QLineEdit):
            editor.setFocus(Qt.FocusReason.MouseFocusReason)
            editor.selectAll()
            return
        if isinstance(editor, QPlainTextEdit):
            editor.setFocus(Qt.FocusReason.MouseFocusReason)
            return
        if isinstance(editor, (QComboBox, QDateEdit, QCheckBox)):
            editor.setFocus(Qt.FocusReason.MouseFocusReason)
            return
        for child_type in (QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QCheckBox):
            child = editor.findChild(child_type)
            if child is not None:
                child.setFocus(Qt.FocusReason.MouseFocusReason)
                return

    def _chip_preview(self, text: str, empty_text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return escape(empty_text)
        chips = []
        palette = self._palette
        for line in lines:
            chips.append(
                f"<span style='display:inline-block; color:{palette.text}; background:{palette.chip_bg}; "
                f"border:1px solid {palette.chip_border}; border-radius:6px; padding:3px 8px; margin:2px;'>"
                f"{escape(line)}</span>"
            )
        return " ".join(chips)

    def _task_types_preview(self) -> str:
        lines = [line.strip() for line in self.task_types_edit.toPlainText().splitlines() if line.strip()]
        if not lines:
            return escape("Типы задач не настроены")
        chips = []
        palette = self._palette
        for line in lines:
            values = self._parse_task_type_line(line)
            title = str(values.get("title") or "")
            value = str(values.get("value") or "")
            color = str(values.get("color_marker") or palette.chip_border)
            priority = str(values.get("priority") or "")
            details = [part for part in (value, priority) if part and part != title]
            if bool(values.get("is_plan_task", False)):
                details.append("План")
            suffix = f" · {' · '.join(details)}" if details else ""
            opacity = "1.0" if bool(values.get("active", True)) else "0.55"
            chips.append(
                f"<span style='display:inline-block; color:{palette.text}; background:{palette.chip_bg}; "
                f"border:1px solid {escape(color)}; border-radius:6px; padding:3px 8px; margin:2px; opacity:{opacity};'>"
                f"{escape(title + suffix)}</span>"
            )
        return " ".join(chips)

    def _display_properties_preview(self) -> str:
        lines = [line.strip() for line in self.display_properties_edit.toPlainText().splitlines() if line.strip()]
        if not lines:
            return escape("Отображаемые свойства не настроены")
        chips = []
        palette = self._palette
        for line in lines[:4]:
            values = self._parse_display_property_line(line)
            name = str(values.get("name") or "")
            url = str(values.get("url") or "")
            mode = str(values.get("display_mode") or "name_link")
            label = f"{name}: {url}" if mode == "url_text" else name
            chips.append(
                f"<span style='display:inline-block; color:{palette.text}; background:{palette.chip_bg}; "
                f"border:1px solid {palette.accent}; border-radius:6px; padding:3px 8px; margin:2px;'>"
                f"{escape(label)}</span>"
            )
        return " ".join(chips)

    def _metric_card(self, title: str, editor: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogMetric")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("ProjectDialogMetricTitle")
        text_box.addWidget(label)
        text_box.addWidget(editor)
        layout.addLayout(text_box, 1)
        return card

    def _section_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogSection")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 11)
        card_layout.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("ProjectDialogSectionTitle")
        card_layout.addWidget(label)
        return card

    def _section_form(self, card: QFrame) -> QFormLayout:
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(7)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout = card.layout()
        if isinstance(layout, QVBoxLayout):
            layout.addLayout(form)
        return form

    def _statistics_row(self) -> QHBoxLayout:
        stats = self._project_statistics()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for title, value in (
            ("Задач", stats["total"]),
            ("Активных", stats["active"]),
            ("Готово", stats["done"]),
            ("Связей", stats["links"]),
        ):
            row.addWidget(self._stat_card(title, value))
        return row

    def _stat_card(self, title: str, value: int) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectDialogMetric")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        label = QLabel(title)
        label.setObjectName("ProjectDialogMetricTitle")
        number = QLabel(str(value))
        number.setObjectName("ProjectDialogSectionTitle")
        layout.addWidget(label)
        layout.addWidget(number)
        return card

    def _project_statistics(self) -> dict[str, int]:
        if self._project is None:
            return {"total": 0, "active": 0, "done": 0, "links": 0}
        project_id = self._project.id
        tasks = [task for task in self._db.fetch_tasks() if getattr(task, "project_id", None) == project_id]
        done = sum(1 for task in tasks if bool(getattr(task, "done", False)))
        links = len(self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты"))
        links += len(self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи"))
        return {"total": len(tasks), "active": len(tasks) - done, "done": done, "links": links}

    def _set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        for control in self._editor_controls:
            control.setEnabled(enabled)
        for button in self._edit_action_buttons:
            button.setVisible(enabled)
            button.setEnabled(enabled)
        self._set_inline_edit_enabled(enabled)
        if hasattr(self, "title_label"):
            self.title_label.setText(self.title_edit.text().strip() or "Новый проект")
        self.mode_label.setText("Редактирование проекта" if enabled else "Просмотр проекта")
        self.close_button.setVisible(not enabled)
        self.edit_button.setVisible(not enabled)
        self.cancel_button.setVisible(enabled)
        self.save_button.setVisible(enabled)
        self._refresh_preview_fields()
        self._sync_content_minimum_height()

    def _save_shortcut(self) -> None:
        if self._edit_mode:
            self._on_accept()

    def _make_multiline_edit(self, placeholder: str) -> QPlainTextEdit:
        edit = QPlainTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(64)
        return edit

    def _make_repository_catalog_editor(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.repository_catalog_edit, 1)
        button = QToolButton()
        button.setText("...")
        button.setObjectName("ProjectDialogIconButton")
        button.setToolTip("Выбрать каталог")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(self._choose_repository_catalog)
        layout.addWidget(button)
        return widget

    def _choose_repository_catalog(self) -> None:
        current_path = self.repository_catalog_edit.text().strip()
        path = QFileDialog.getExistingDirectory(self, "Каталог репозитория", current_path)
        if path:
            self.repository_catalog_edit.setText(path)

    def _make_property_editor(self, edit: QPlainTextEdit, actions: list[tuple[str, object]]) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(edit)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        action_row.addStretch(1)
        for text, callback in actions:
            button = QToolButton()
            button.setText(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        layout.addLayout(action_row)
        return widget

    def _make_reflect_checkbox(self) -> QCheckBox:
        checkbox = QCheckBox("Отразить в задачах")
        checkbox.setToolTip("Показать это свойство в задачах проекта как «Текст ссылки».")
        checkbox.toggled.connect(lambda _checked=False: self._refresh_preview_fields())
        return checkbox

    def _make_reflectable_editor(self, editor: QWidget, checkbox: QCheckBox) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(editor)
        layout.addWidget(checkbox)
        return widget

    def _make_inline_property_editor(self, edit: QPlainTextEdit, kind: str, add_callback: object) -> QWidget:
        edit.setVisible(False)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        editor = EditableListWidget(icon_color=self._palette.text)
        editor.addRequested.connect(add_callback)
        editor.editRequested.connect(lambda index, row_kind=kind: self._edit_inline_property(row_kind, index))
        editor.deleteRequested.connect(lambda index, row_kind=kind: self._delete_inline_property(row_kind, index))
        if kind == "task_types":
            editor.actionRequested.connect(self._toggle_inline_task_type)
        layout.addWidget(edit)
        layout.addWidget(editor)
        setattr(self, f"{kind}_list_widget", editor.rows_widget)
        setattr(self, f"{kind}_list_editor", editor)
        return widget

    def _refresh_inline_property_lists(self) -> None:
        for kind, edit_name in (
            ("task_types", "task_types_edit"),
            ("display_properties", "display_properties_edit"),
            ("related_projects", "related_projects_edit"),
            ("related_tasks", "related_tasks_edit"),
            ("repository_links", "repository_links_edit"),
            ("wiki_links", "wiki_links_edit"),
        ):
            editor = getattr(self, f"{kind}_list_editor", None)
            edit = getattr(self, edit_name, None)
            if editor is not None and edit is not None:
                items = []
                for line in (line.strip() for line in edit.toPlainText().splitlines() if line.strip()):
                    action_icon = ""
                    action_tooltip = ""
                    detail = ""
                    marker_color = ""
                    if kind == "task_types":
                        values = self._parse_task_type_line(line)
                        active = bool(values.get("active", True))
                        action_icon = "fa5s.check" if active else "fa5s.ban"
                        action_tooltip = "Активировать/деактивировать"
                        detail = self._task_type_inline_detail(values)
                        marker_color = str(values.get("color_marker") or "")
                    items.append(
                        EditableListItem(
                            label=self._inline_property_label(kind, line),
                            action_icon=action_icon,
                            action_tooltip=action_tooltip,
                            detail=detail,
                            marker_color=marker_color,
                        )
                    )
                editor.set_items(items)
        if hasattr(self, "_edit_mode"):
            self._set_inline_edit_enabled(self._edit_mode)
            self._sync_content_minimum_height()

    def _set_inline_edit_enabled(self, enabled: bool) -> None:
        for kind in (
            "task_types",
            "display_properties",
            "related_projects",
            "related_tasks",
            "repository_links",
            "wiki_links",
        ):
            editor = getattr(self, f"{kind}_list_editor", None)
            if editor is not None:
                editor.set_edit_enabled(enabled)

    def _sync_content_minimum_height(self) -> None:
        content = getattr(self, "_content_widget", None)
        layout = getattr(self, "_content_layout", None)
        if content is None or layout is None:
            return
        if not self._edit_mode:
            content.setMinimumHeight(0)
            return
        layout.activate()
        columns = getattr(self, "_content_columns", ())
        for column in columns:
            column.activate()
        card_columns = getattr(self, "_content_card_columns", ())
        minimum_height = max(
            (
                sum(card.sizeHint().height() for card in cards) + 10 * max(0, len(cards) - 1)
                for cards in card_columns
            ),
            default=0,
        )
        content.setMinimumHeight(max(layout.minimumSize().height(), minimum_height))

    def _inline_property_label(self, kind: str, line: str) -> str:
        if kind == "task_types":
            values = self._parse_task_type_line(line)
            return str(values.get("title") or "")
        if kind == "display_properties":
            values = self._parse_display_property_line(line)
            return str(values.get("name") or "")
        if kind in {"repository_links", "wiki_links"}:
            values = self._parse_link_line(line)
            return str(values.get("title") or values.get("url") or "")
        if kind == "related_projects":
            project_id = self._line_int_or_none(line)
            project = self._project_by_id(project_id)
            return f"{project.area} / {project.title}" if project is not None else line.strip()
        if kind == "related_tasks":
            task_id = self._line_int_or_none(line)
            task = self._task_by_id(task_id)
            return f"MN-{task.id} {task.title}" if task is not None else line.strip()
        return line.strip()

    @staticmethod
    def _task_type_inline_detail(values: dict[str, object]) -> str:
        parts = []
        value = str(values.get("value") or "").strip()
        priority = str(values.get("priority") or "").strip()
        if value:
            parts.append(value)
        if priority:
            parts.append(priority)
        parts.append(f"Важн. {int(values.get('importance') or 3)}")
        if bool(values.get("is_plan_task", False)):
            parts.append("План")
        return " · ".join(parts)

    def _edit_inline_property(self, kind: str, line_index: int) -> None:
        if kind == "task_types":
            self._edit_task_type_line(line_index)
        elif kind == "display_properties":
            self._edit_display_property_line(line_index)
        elif kind == "related_projects":
            self._edit_related_project_line(line_index)
        elif kind == "related_tasks":
            self._edit_related_task_line(line_index)
        elif kind == "repository_links":
            self._edit_link_line(self.repository_links_edit, "Репозиторий", line_index)
        elif kind == "wiki_links":
            self._edit_link_line(self.wiki_links_edit, "Wiki", line_index)

    def _delete_inline_property(self, kind: str, line_index: int) -> None:
        if kind == "task_types":
            self._delete_task_type_line(line_index)
        elif kind == "display_properties":
            self._delete_display_property_line(line_index)
        elif kind == "related_projects":
            self._remove_line(self.related_projects_edit, line_index)
        elif kind == "related_tasks":
            self._remove_line(self.related_tasks_edit, line_index)
        elif kind == "repository_links":
            self._remove_line(self.repository_links_edit, line_index)
        elif kind == "wiki_links":
            self._remove_line(self.wiki_links_edit, line_index)

    def _toggle_inline_task_type(self, line_index: int) -> None:
        self._toggle_task_type_line(line_index)

    def _apply_child_dialog_style(self, dialog: QDialog) -> None:
        palette = self._palette
        dialog.setStyleSheet(f"""
            QDialog {{
                background: {palette.panel_bg};
                color: {palette.text};
            }}

            QLabel {{
                color: {palette.text};
            }}

            QLineEdit,
            QComboBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 30px;
            }}

            QCheckBox {{
                color: {palette.text};
                padding: 4px 0;
            }}

            QPushButton {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 6px;
                padding: 8px 16px;
                min-width: 104px;
            }}

            QPushButton:hover {{
                background: {palette.selection_bg};
            }}

            QDialogButtonBox QPushButton {{
                min-width: 116px;
            }}
        """)

    def _append_line(self, edit: QPlainTextEdit, line: str) -> None:
        line = (line or "").strip()
        if not line:
            return
        text = edit.toPlainText().strip()
        edit.setPlainText(f"{text}\n{line}" if text else line)
        self._refresh_inline_property_lists()
        self._refresh_preview_fields()

    def _current_line_info(self, edit: QPlainTextEdit) -> tuple[list[str], int, str]:
        lines = edit.toPlainText().splitlines()
        if not lines:
            return lines, -1, ""
        cursor = edit.textCursor()
        line_index = min(max(0, cursor.blockNumber()), len(lines) - 1)
        return lines, line_index, lines[line_index].strip()

    def _replace_line(self, edit: QPlainTextEdit, line_index: int, line: str) -> None:
        lines = edit.toPlainText().splitlines()
        if line_index < 0 or line_index >= len(lines):
            return
        lines[line_index] = line
        edit.setPlainText("\n".join(lines))
        cursor = edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_index):
            cursor.movePosition(cursor.MoveOperation.Down)
        edit.setTextCursor(cursor)
        self._refresh_inline_property_lists()
        self._refresh_preview_fields()

    def _remove_line(self, edit: QPlainTextEdit, line_index: int) -> None:
        lines = edit.toPlainText().splitlines()
        if line_index < 0 or line_index >= len(lines):
            return
        del lines[line_index]
        edit.setPlainText("\n".join(lines))
        self._refresh_inline_property_lists()
        self._refresh_preview_fields()

    def _copy_combo_items(self, source: QComboBox, target: QComboBox) -> None:
        for idx in range(source.count()):
            target.addItem(source.itemText(idx), source.itemData(idx))

    @staticmethod
    def _line_int_or_none(line: str) -> Optional[int]:
        try:
            return int((line or "").strip())
        except ValueError:
            return None

    def _project_by_id(self, project_id: Optional[int]):
        if project_id is None:
            return None
        return next((project for project in self._db.fetch_projects() if project.id == project_id), None)

    def _task_by_id(self, task_id: Optional[int]):
        if task_id is None:
            return None
        return next((task for task in self._db.fetch_tasks() if task.id == task_id), None)

    def _task_type_section_title(self, icon_name: str, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=self._palette.text).pixmap(22, 22))
        label = QLabel(text)
        label.setObjectName("TaskTypeSectionTitle")
        row.addWidget(icon)
        row.addWidget(label)
        row.addStretch(1)
        return row

    def _task_type_field_label(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(7)
        label = QLabel(text)
        label.setObjectName("TaskTypeFieldLabel")
        help_icon = QLabel()
        help_icon.setPixmap(qta.icon("fa5s.question-circle", color=self._palette.dim_text).pixmap(14, 14))
        row.addWidget(label)
        row.addWidget(help_icon)
        row.addStretch(1)
        return row

    def _task_type_rule_row(self, icon_name: str, color: str, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        icon = QLabel()
        icon.setObjectName("TaskTypeRuleIcon")
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        label = QLabel(text)
        label.setObjectName("TaskTypeRuleText")
        label.setWordWrap(True)
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(label, 1)
        return row

    def _task_type_separator(self) -> QFrame:
        separator = QFrame()
        separator.setObjectName("TaskTypePreviewSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        return separator

    def _task_type_preview_row(self, icon_name: str, color: str, label_text: str) -> tuple[QHBoxLayout, QLabel]:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        label = QLabel(f"{label_text}:")
        label.setObjectName("TaskTypePreviewLabel")
        value = QLabel()
        value.setObjectName("TaskTypePreviewValue")
        value.setWordWrap(True)
        row.addWidget(icon)
        row.addWidget(label)
        row.addWidget(value, 1)
        return row, value

    def _apply_task_type_dialog_style(self, dialog: QDialog) -> None:
        palette = self._palette
        dialog.setStyleSheet(f"""
            QDialog#ProjectTaskTypeDialog {{
                background: {palette.window_bg};
            }}

            QFrame#TaskTypeCard,
            QFrame#TaskTypePreviewCard {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QLabel#TaskTypeDialogTitle {{
                color: {palette.selection_text};
                font-size: 21px;
                font-weight: 700;
            }}

            QLabel#TaskTypeDialogSubtitle,
            QLabel#TaskTypeFieldHint,
            QLabel#TaskTypePreviewCaption,
            QLabel#TaskTypePreviewText {{
                color: {palette.dim_text};
                font-size: 12px;
            }}

            QLabel#TaskTypeSectionTitle,
            QLabel#TaskTypePreviewTitle {{
                color: {palette.selection_text};
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#TaskTypeFieldLabel,
            QLabel#TaskTypePreviewLabel,
            QLabel#TaskTypeRuleText {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#TaskTypePreviewValue {{
                color: {palette.text};
                font-size: 13px;
            }}

            QLabel#TaskTypePreviewBadge {{
                color: #20f5d2;
                background: rgba(32, 245, 210, 0.10);
                border: 1px solid #20f5d2;
                border-radius: 18px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 800;
            }}

            QFrame#TaskTypePreviewSeparator {{
                background: {palette.border};
                border: none;
            }}

            QDialog#ProjectTaskTypeDialog QLineEdit,
            QDialog#ProjectTaskTypeDialog QComboBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 9px;
                min-height: 28px;
            }}

            QDialog#ProjectTaskTypeDialog QLineEdit:focus,
            QDialog#ProjectTaskTypeDialog QComboBox:focus {{
                border: 1px solid {palette.accent};
            }}

            QDialog#ProjectTaskTypeDialog QCheckBox {{
                color: {palette.text};
                font-size: 13px;
                padding: 4px 0;
            }}

            QDialog#ProjectTaskTypeDialog QPushButton {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 7px;
                padding: 7px 12px;
                min-width: 104px;
            }}

            QDialog#ProjectTaskTypeDialog QPushButton:hover {{
                background: {palette.selection_bg};
            }}

            QPushButton#TaskTypeDialogPrimaryButton {{
                background: {palette.accent};
                border: 1px solid {palette.accent_hover};
                color: {palette.selection_text};
                font-weight: 700;
                min-width: 126px;
            }}

            QPushButton#TaskTypeDialogSecondaryButton {{
                min-width: 108px;
            }}
        """)

    def _display_property_section_title(self, icon_name: str, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=self._palette.text).pixmap(22, 22))
        label = QLabel(text)
        label.setObjectName("DisplayPropertySectionTitle")
        row.addWidget(icon)
        row.addWidget(label)
        row.addStretch(1)
        return row

    def _display_property_field_label(self, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(7)
        label = QLabel(text)
        label.setObjectName("DisplayPropertyFieldLabel")
        help_icon = QLabel()
        help_icon.setPixmap(qta.icon("fa5s.question-circle", color=self._palette.dim_text).pixmap(14, 14))
        row.addWidget(label)
        row.addWidget(help_icon)
        row.addStretch(1)
        return row

    def _display_mode_card(self, icon_name: str, title: str, text: str, value: str) -> tuple[QRadioButton, QFrame]:
        card = QFrame()
        card.setObjectName("DisplayModeCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        radio = QRadioButton()
        radio.setProperty("display_mode", value)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=self._palette.accent).pixmap(20, 20))
        text_box = QVBoxLayout()
        text_box.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("DisplayModeTitle")
        body_label = QLabel(text)
        body_label.setObjectName("DisplayModeText")
        body_label.setWordWrap(True)
        text_box.addWidget(title_label)
        text_box.addWidget(body_label)
        layout.addWidget(radio, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_box, 1)
        card.mousePressEvent = lambda _event: radio.setChecked(True)
        return radio, card

    def _display_property_rule_row(self, icon_name: str, color: str, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        label = QLabel(text)
        label.setObjectName("DisplayPropertyRuleText")
        label.setWordWrap(True)
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(label, 1)
        return row

    def _display_property_separator(self) -> QFrame:
        separator = QFrame()
        separator.setObjectName("DisplayPropertyPreviewSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        return separator

    def _apply_display_property_dialog_style(self, dialog: QDialog) -> None:
        palette = self._palette
        dialog.setStyleSheet(f"""
            QDialog#ProjectDisplayPropertyDialog {{
                background: {palette.window_bg};
            }}

            QFrame#DisplayPropertyCard,
            QFrame#DisplayPropertyPreviewCard {{
                background: {palette.elevated_bg};
                border: 1px solid {palette.border};
                border-radius: 10px;
            }}

            QFrame#DisplayModeCard {{
                background: {palette.input_alt_bg};
                border: 1px solid {palette.border};
                border-radius: 9px;
            }}

            QFrame#DisplayModeCard:hover {{
                border: 1px solid {palette.accent};
            }}

            QLabel#DisplayPropertyDialogTitle {{
                color: {palette.selection_text};
                font-size: 21px;
                font-weight: 700;
            }}

            QLabel#DisplayPropertyDialogSubtitle,
            QLabel#DisplayPropertyFieldHint,
            QLabel#DisplayPropertyPreviewCaption,
            QLabel#DisplayPropertyPreviewText,
            QLabel#DisplayModeText {{
                color: {palette.dim_text};
                font-size: 12px;
            }}

            QLabel#DisplayPropertySectionTitle,
            QLabel#DisplayPropertyPreviewTitle {{
                color: {palette.selection_text};
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#DisplayPropertyFieldLabel,
            QLabel#DisplayPropertyPreviewLabel,
            QLabel#DisplayPropertyRuleText,
            QLabel#DisplayModeTitle {{
                color: {palette.text};
                font-size: 13px;
                font-weight: 600;
            }}

            QLabel#DisplayPropertyPreviewBadge {{
                color: #20f5d2;
                background: rgba(32, 245, 210, 0.10);
                border: 1px solid #20f5d2;
                border-radius: 18px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 800;
            }}

            QLabel#DisplayPropertyPreviewLink {{
                color: #20f5d2;
                background: rgba(32, 245, 210, 0.08);
                border: 1px solid #20f5d2;
                border-radius: 7px;
                padding: 6px 10px;
                font-weight: 700;
            }}

            QLabel#DisplayPropertyPreviewUrl {{
                color: {palette.text};
                background: {palette.input_bg};
                border: 1px solid {palette.border};
                border-radius: 7px;
                padding: 6px 10px;
            }}

            QFrame#DisplayPropertyPreviewSeparator {{
                background: {palette.border};
                border: none;
            }}

            QDialog#ProjectDisplayPropertyDialog QLineEdit,
            QDialog#ProjectDisplayPropertyDialog QSpinBox {{
                background: {palette.input_bg};
                color: {palette.text};
                border: 1px solid {palette.border};
                border-radius: 6px;
                padding: 6px 9px;
                min-height: 28px;
            }}

            QDialog#ProjectDisplayPropertyDialog QLineEdit:focus,
            QDialog#ProjectDisplayPropertyDialog QSpinBox:focus {{
                border: 1px solid {palette.accent};
            }}

            QDialog#ProjectDisplayPropertyDialog QRadioButton {{
                color: {palette.text};
            }}

            QDialog#ProjectDisplayPropertyDialog QPushButton {{
                background: {palette.panel_alt_bg};
                color: {palette.text};
                border: 1px solid {palette.border_strong};
                border-radius: 7px;
                padding: 7px 12px;
                min-width: 104px;
            }}

            QDialog#ProjectDisplayPropertyDialog QPushButton:hover {{
                background: {palette.selection_bg};
            }}

            QPushButton#DisplayPropertyDialogPrimaryButton {{
                background: {palette.accent};
                border: 1px solid {palette.accent_hover};
                color: {palette.selection_text};
                font-weight: 700;
                min-width: 126px;
            }}

            QPushButton#DisplayPropertyDialogSecondaryButton {{
                min-width: 108px;
            }}
        """)

    def _add_task_type_line(self) -> None:
        values = self._task_type_dialog()
        if values is None:
            return
        self._append_line(self.task_types_edit, self._format_task_type_line(values))

    def _edit_task_type_line(self, line_index: Optional[int] = None) -> None:
        lines, current_line_index, line = self._current_line_info(self.task_types_edit)
        if line_index is None:
            line_index = current_line_index
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        updated = self._task_type_dialog(values)
        if updated is None:
            return
        self._replace_line(self.task_types_edit, line_index, self._format_task_type_line(updated))

    def _toggle_task_type_line(self, line_index: Optional[int] = None) -> None:
        lines, current_line_index, line = self._current_line_info(self.task_types_edit)
        if line_index is None:
            line_index = current_line_index
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        values["active"] = not bool(values.get("active", True))
        self._replace_line(self.task_types_edit, line_index, self._format_task_type_line(values))

    def _delete_task_type_line(self, line_index: Optional[int] = None) -> None:
        lines, current_line_index, line = self._current_line_info(self.task_types_edit)
        if line_index is None:
            line_index = current_line_index
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if line_index < 0 or not line:
            return
        values = self._parse_task_type_line(line)
        title = str(values.get("title") or "")
        if self._project:
            existing = next(
                (
                    item
                    for item in self._db.fetch_project_task_types(self._project.id, include_inactive=True)
                    if item.title == title
                ),
                None,
            )
            if existing is not None and self._db.project_task_type_in_use(existing.id):
                QMessageBox.warning(
                    self,
                    "Тип задач",
                    "Тип используется задачами. Деактивируйте тип вместо удаления.",
                )
                return
        if QMessageBox.question(self, "Тип задач", f"Удалить тип {title}?") != QMessageBox.StandardButton.Yes:
            return
        self._remove_line(self.task_types_edit, line_index)

    def _task_type_dialog(self, initial: Optional[dict[str, object]] = None) -> Optional[dict[str, object]]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Тип задач")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("DEV")
        if initial:
            title_edit.setText(str(initial.get("title") or ""))
        color_combo = QComboBox()
        self._copy_combo_items(self.marker_color_edit, color_combo)
        if initial:
            color_idx = color_combo.findData(str(initial.get("color_marker") or ""))
            if color_idx >= 0:
                color_combo.setCurrentIndex(color_idx)
        theme_combo = QComboBox()
        self._copy_combo_items(self.marker_theme_edit, theme_combo)
        if initial:
            theme_idx = theme_combo.findData(str(initial.get("theme_marker") or ""))
            if theme_idx >= 0:
                theme_combo.setCurrentIndex(theme_idx)
        active_edit = QCheckBox("Активен")
        active_edit.setChecked(bool(initial.get("active", True)) if initial else True)
        form.addRow("Название", title_edit)
        form.addRow("Цвет", color_combo)
        form.addRow("Тема", theme_combo)
        form.addRow("", active_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        title = " ".join(title_edit.text().strip().upper().split())
        if not title:
            QMessageBox.warning(self, "Проверка", "Название типа задач не должно быть пустым.")
            return None
        return {
            "title": title,
            "color_marker": color_combo.currentData() or "",
            "theme_marker": theme_combo.currentData() or "",
            "active": active_edit.isChecked(),
        }

    @staticmethod
    def _format_task_type_line(values: dict[str, object]) -> str:
        status = "active" if bool(values.get("active", True)) else "disabled"
        title = " ".join(str(values.get("title") or "").strip().upper().split())
        return f"{title} | {values.get('color_marker') or ''} | {values.get('theme_marker') or ''} | {status}"

    @staticmethod
    def _parse_task_type_line(line: str) -> dict[str, object]:
        parts = [part.strip() for part in (line or "").split("|")]
        title = " ".join((parts[0] if parts else "").strip().upper().split())
        status = (parts[3] if len(parts) > 3 else "active").strip().lower()
        return {
            "title": title,
            "color_marker": parts[1] if len(parts) > 1 else "",
            "theme_marker": parts[2] if len(parts) > 2 else "",
            "active": status not in {"disabled", "inactive", "off", "0", "false"},
        }

    def _task_type_dialog(self, initial: Optional[dict[str, object]] = None) -> Optional[dict[str, object]]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование типа задач" if initial else "Создание типа задач")
        dialog.setObjectName("ProjectTaskTypeDialog")
        dialog.resize(900, 620)
        dialog.setMinimumSize(820, 560)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        hero_icon = QLabel()
        hero_icon.setObjectName("TaskTypeDialogHeroIcon")
        hero_icon.setPixmap(qta.icon("fa5s.tag", color="#5f7cff").pixmap(26, 26))
        header.addWidget(hero_icon, 0, Qt.AlignmentFlag.AlignTop)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_label = QLabel("Редактирование типа задач" if initial else "Создание типа задач")
        title_label.setObjectName("TaskTypeDialogTitle")
        subtitle_label = QLabel("Настройка кастомного типа задач проекта")
        subtitle_label.setObjectName("TaskTypeDialogSubtitle")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header.addLayout(title_box, 1)
        preview_button = QPushButton("Предпросмотр")
        preview_button.setObjectName("TaskTypeDialogSecondaryButton")
        preview_button.setIcon(qta.icon("fa5s.eye", color=self._palette.text))
        close_button = QPushButton("Закрыть")
        close_button.setObjectName("TaskTypeDialogSecondaryButton")
        close_button.setIcon(qta.icon("fa5s.times", color=self._palette.text))
        close_button.clicked.connect(dialog.reject)
        header.addWidget(preview_button)
        header.addWidget(close_button)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        body.addLayout(left_column, 1)
        preview_card = QFrame()
        preview_card.setObjectName("TaskTypePreviewCard")
        preview_card.setMinimumWidth(280)
        preview_card.setMaximumWidth(320)
        body.addWidget(preview_card)
        root.addLayout(body, 1)

        main_card = QFrame()
        main_card.setObjectName("TaskTypeCard")
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)
        main_layout.addLayout(self._task_type_section_title("fa5s.clipboard-list", "Основное"))
        left_column.addWidget(main_card)

        title_grid = QGridLayout()
        title_grid.setHorizontalSpacing(12)
        title_grid.setVerticalSpacing(6)
        title_edit = QLineEdit(str(initial.get("title") or "") if initial else "")
        title_edit.setPlaceholderText("Разработка")
        value_edit = QLineEdit(str(initial.get("value") or initial.get("title") or "") if initial else "")
        value_edit.setPlaceholderText("DEV")
        value_hint = QLabel("Английское значение, одно слово. Хранится и отображается в верхнем регистре.")
        value_hint.setObjectName("TaskTypeFieldHint")
        value_hint.setWordWrap(True)
        title_grid.addLayout(self._task_type_field_label("Название"), 0, 0)
        title_grid.addLayout(self._task_type_field_label("Значение"), 0, 1)
        title_grid.addWidget(title_edit, 1, 0)
        title_grid.addWidget(value_edit, 1, 1)
        title_grid.addWidget(QLabel(""), 2, 0)
        title_grid.addWidget(value_hint, 2, 1)
        main_layout.addLayout(title_grid)

        inherit_grid = QGridLayout()
        inherit_grid.setHorizontalSpacing(12)
        inherit_grid.setVerticalSpacing(8)
        color_combo = QComboBox()
        self._copy_combo_items(self.marker_color_edit, color_combo)
        theme_combo = QComboBox()
        self._copy_combo_items(self.marker_theme_edit, theme_combo)
        priority_combo = QComboBox()
        for label, value in (("None", ""), ("High", "High"), ("Medium", "Medium"), ("Low", "Low")):
            priority_combo.addItem(label, value)
        importance_combo = QComboBox()
        for value in range(1, 6):
            importance_combo.addItem(str(value), value)
        concept_combo = QComboBox()
        concept_combo.addItem("None", None)
        fetch_boards = getattr(self._db, "fetch_concept_boards", None)
        if callable(fetch_boards):
            for board in fetch_boards():
                concept_combo.addItem(board.title, board.id)
        plan_combo = QComboBox()
        plan_combo.addItem("Нет", False)
        plan_combo.addItem("Да, плановая", True)
        active_edit = QCheckBox("Тип задач активен")
        active_edit.setChecked(True)
        if initial:
            for combo, key in (
                (color_combo, "color_marker"),
                (theme_combo, "theme_marker"),
                (priority_combo, "priority"),
                (importance_combo, "importance"),
                (concept_combo, "concept_board_id"),
            ):
                idx = combo.findData(initial.get(key))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            plan_idx = plan_combo.findData(bool(initial.get("is_plan_task", False)))
            if plan_idx >= 0:
                plan_combo.setCurrentIndex(plan_idx)
            active_edit.setChecked(bool(initial.get("active", True)))

        for label, editor, row, column in (
            ("Маркер", color_combo, 0, 0),
            ("Тематика маркера", theme_combo, 0, 1),
            ("Приоритет", priority_combo, 1, 0),
            ("Важность", importance_combo, 1, 1),
            ("План-задача", plan_combo, 2, 0),
            ("Концептборд", concept_combo, 2, 1),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(7)
            cell.addLayout(self._task_type_field_label(label))
            cell.addWidget(editor)
            inherit_grid.addLayout(cell, row, column)
        main_layout.addLayout(inherit_grid)
        main_layout.addWidget(active_edit)
        active_note = QLabel("Если отключить, тип не будет доступен для новых задач")
        active_note.setObjectName("TaskTypeFieldHint")
        main_layout.addWidget(active_note)

        rules_card = QFrame()
        rules_card.setObjectName("TaskTypeCard")
        rules_layout = QVBoxLayout(rules_card)
        rules_layout.setContentsMargins(14, 12, 14, 14)
        rules_layout.setSpacing(8)
        rules_layout.addLayout(self._task_type_section_title("fa5s.shield-alt", "Правила и ограничения"))
        for icon_name, color, text in (
            ("fa5s.info-circle", "#3478f6", "Значение должно быть уникальным в рамках проекта."),
            ("fa5s.exclamation-triangle", "#f0a72f", "В одном проекте нельзя повторять Маркер у разных типов."),
            ("fa5s.th-large", "#8a63d2", "Свойства наследуются задачей после выбора типа."),
        ):
            rules_layout.addLayout(self._task_type_rule_row(icon_name, color, text))
        left_column.addWidget(rules_card)
        left_column.addStretch(1)

        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 12, 14, 14)
        preview_layout.setSpacing(10)
        preview_layout.addLayout(self._task_type_section_title("fa5s.eye", "Предпросмотр"))
        badge_caption = QLabel("Бейдж типа")
        badge_caption.setObjectName("TaskTypePreviewCaption")
        preview_layout.addWidget(badge_caption)
        badge_label = QLabel()
        badge_label.setObjectName("TaskTypePreviewBadge")
        badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_label.setMinimumWidth(150)
        preview_layout.addWidget(badge_label, 0, Qt.AlignmentFlag.AlignLeft)
        preview_layout.addWidget(self._task_type_separator())
        inherit_title = QLabel("Наследуемые свойства")
        inherit_title.setObjectName("TaskTypePreviewTitle")
        preview_layout.addWidget(inherit_title)
        preview_rows: dict[str, QLabel] = {}
        for icon_name, color, label in (
            ("fa5s.square", "#20f5d2", "Маркер"),
            ("fa5s.bug", "#aeb6c8", "Тематика"),
            ("fa5s.angle-double-up", "#ff4747", "Приоритет"),
            ("fa5s.ellipsis-h", "#ff9f1c", "Важность"),
            ("fa5s.calendar-check", "#43c463", "План-задача"),
            ("fa5s.th-large", "#9b75ff", "Концептборд"),
        ):
            row_layout, value_label = self._task_type_preview_row(icon_name, color, label)
            preview_rows[label] = value_label
            preview_layout.addLayout(row_layout)
        preview_layout.addWidget(self._task_type_separator())
        about_title = QLabel("О типе задачи  ⓘ")
        about_title.setObjectName("TaskTypePreviewTitle")
        preview_layout.addWidget(about_title)
        about_text = QLabel(
            "При выборе этого типа для задачи будут применены указанные свойства. "
            "Пользователь сможет изменить их вручную после создания задачи."
        )
        about_text.setObjectName("TaskTypePreviewText")
        about_text.setWordWrap(True)
        preview_layout.addWidget(about_text)
        preview_layout.addStretch(1)
        preview_button.clicked.connect(lambda: preview_card.setFocus(Qt.FocusReason.OtherFocusReason))

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 0, 0)
        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("TaskTypeDialogSecondaryButton")
        cancel_button.setIcon(qta.icon("fa5s.times", color=self._palette.text))
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Сохранить")
        save_button.setObjectName("TaskTypeDialogPrimaryButton")
        save_button.setIcon(qta.icon("fa5s.save", color=self._palette.selection_text))
        save_more_button = QPushButton("Сохранить и добавить ещё")
        save_more_button.setObjectName("TaskTypeDialogSecondaryButton")
        save_more_button.setIcon(qta.icon("fa5s.plus-circle", color=self._palette.text))
        save_button.clicked.connect(dialog.accept)
        save_more_button.clicked.connect(dialog.accept)
        footer.addWidget(cancel_button)
        footer.addStretch(1)
        footer.addWidget(save_button)
        footer.addWidget(save_more_button)
        root.addLayout(footer)

        def update_preview() -> None:
            title_text = " ".join(title_edit.text().strip().upper().split()) or "РАЗРАБОТКА"
            value_text = "".join(value_edit.text().strip().upper().split()) or "DEV"
            badge_label.setText(f"{title_text} · {value_text}")
            preview_rows["Маркер"].setText(color_combo.currentText().strip() or "None")
            preview_rows["Тематика"].setText(theme_combo.currentText().strip() or "None")
            preview_rows["Приоритет"].setText(priority_combo.currentText().strip() or "None")
            preview_rows["Важность"].setText(importance_combo.currentText().strip() or "3")
            preview_rows["План-задача"].setText("Да, плановая" if bool(plan_combo.currentData()) else "Нет")
            preview_rows["Концептборд"].setText(concept_combo.currentText().strip() or "None")

        for editor in (title_edit, value_edit):
            editor.textChanged.connect(update_preview)
        for combo in (color_combo, theme_combo, priority_combo, importance_combo, plan_combo, concept_combo):
            combo.currentIndexChanged.connect(update_preview)
        update_preview()
        self._apply_task_type_dialog_style(dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        title = " ".join(title_edit.text().strip().upper().split())
        value = "".join(value_edit.text().strip().upper().split())
        if not title or not value:
            QMessageBox.warning(self, "Проверка", "Название и значение типа задачи обязательны.")
            return None
        return {
            "title": title,
            "value": value,
            "color_marker": color_combo.currentData() or "",
            "theme_marker": theme_combo.currentData() or "",
            "priority": priority_combo.currentData() or "",
            "importance": int(importance_combo.currentData() or 3),
            "is_plan_task": bool(plan_combo.currentData()),
            "concept_board_id": concept_combo.currentData(),
            "active": active_edit.isChecked(),
        }

    @staticmethod
    def _format_task_type_line(values: dict[str, object]) -> str:
        status = "active" if bool(values.get("active", True)) else "disabled"
        title = " ".join(str(values.get("title") or "").strip().upper().split())
        value = "".join(str(values.get("value") or title).strip().upper().split())
        return (
            f"{title} | {value} | {values.get('color_marker') or ''} | {values.get('theme_marker') or ''} | "
            f"{values.get('priority') or ''} | {int(values.get('importance') or 3)} | "
            f"{1 if bool(values.get('is_plan_task', False)) else 0} | {values.get('concept_board_id') or ''} | {status}"
        )

    @staticmethod
    def _parse_task_type_line(line: str) -> dict[str, object]:
        parts = [part.strip() for part in (line or "").split("|")]
        title = " ".join((parts[0] if parts else "").strip().upper().split())
        legacy = len(parts) <= 4
        status = (parts[3] if legacy and len(parts) > 3 else (parts[8] if len(parts) > 8 else "active")).strip().lower()
        importance = 3
        if not legacy and len(parts) > 5 and parts[5]:
            importance = int(parts[5])
        return {
            "title": title,
            "value": title if legacy else (parts[1] if len(parts) > 1 else title),
            "color_marker": parts[1] if legacy and len(parts) > 1 else (parts[2] if len(parts) > 2 else ""),
            "theme_marker": parts[2] if legacy and len(parts) > 2 else (parts[3] if len(parts) > 3 else ""),
            "priority": "" if legacy else (parts[4] if len(parts) > 4 else ""),
            "importance": importance,
            "is_plan_task": False if legacy else (parts[6] if len(parts) > 6 else "") in {"1", "true", "yes", "on"},
            "concept_board_id": None if legacy or len(parts) <= 7 or not parts[7] else int(parts[7]),
            "active": status not in {"disabled", "inactive", "off", "0", "false"},
        }

    def _add_related_project_line(self) -> None:
        item_id = self._select_related_item("project", "Связанный проект")
        if item_id is not None:
            self._append_unique_int_line(self.related_projects_edit, item_id)

    def _edit_related_project_line(self, line_index: int) -> None:
        item_id = self._select_related_item("project", "Связанный проект")
        if item_id is not None:
            self._replace_line(self.related_projects_edit, line_index, str(item_id))

    def _add_related_task_line(self) -> None:
        item_id = self._select_related_item("task", "Связанная задача")
        if item_id is not None:
            self._append_unique_int_line(self.related_tasks_edit, item_id)

    def _edit_related_task_line(self, line_index: int) -> None:
        item_id = self._select_related_item("task", "Связанная задача")
        if item_id is not None:
            self._replace_line(self.related_tasks_edit, line_index, str(item_id))

    def _select_related_item(self, kind: str, title: str) -> Optional[int]:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setObjectName("ProjectCompactRelationDialog")
        dialog.setFixedSize(550, 200)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        combo = FilterableComboBox(dialog)
        combo.setMinimumContentsLength(24)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo_view = combo.view()
        if combo_view is not None:
            combo_view.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        for item_id, label in self._relation_candidates(kind):
            combo.addItem(label, item_id)
        if combo.count() == 0:
            combo.addItem("— нет доступных —", None)
        form.addRow("Элемент", combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        self._apply_child_dialog_style(dialog)
        if combo.count() and dialog.exec() == QDialog.DialogCode.Accepted:
            item_id = combo.currentData()
            return int(item_id) if item_id is not None else None
        return None

    def _add_relation_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить связь")
        dialog.setObjectName("ProjectCompactRelationDialog")
        dialog.setFixedSize(620, 360)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        type_combo = QComboBox()
        type_combo.addItem("Проект", "project")
        type_combo.addItem("Задача", "task")
        type_combo.addItem("Карта", "map")
        type_combo.addItem("Заметка", "note")
        type_combo.addItem("Объект", "object")
        type_combo.addItem("Репозиторий", "repository")
        type_combo.addItem("Wiki", "wiki")
        layout.addWidget(type_combo)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Поиск связи")
        layout.addWidget(search_edit)

        result_list = QListWidget()
        layout.addWidget(result_list, 1)

        manual_form = QWidget()
        manual_layout = QFormLayout(manual_form)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("Название")
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("Ссылка или путь")
        manual_layout.addRow("Название", title_edit)
        manual_layout.addRow("Ссылка", url_edit)
        layout.addWidget(manual_form)

        selected_label = QLabel("Выберите связь из списка")
        selected_label.setObjectName("ProjectDialogMode")
        layout.addWidget(selected_label)

        buttons = QDialogButtonBox(dialog)
        add_button = buttons.addButton("Добавить связь", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def populate() -> None:
            kind = str(type_combo.currentData() or "")
            query = search_edit.text().strip().lower()
            result_list.clear()
            manual = kind in {"repository", "wiki"}
            result_list.setVisible(not manual)
            search_edit.setVisible(not manual)
            manual_form.setVisible(manual)
            selected_label.setText("Укажите название и ссылку" if manual else "Выберите связь из списка")
            add_button.setEnabled(manual)
            if manual:
                return
            for item_id, label in self._relation_candidates(kind):
                if query and query not in label.lower():
                    continue
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, (kind, item_id, label))
                result_list.addItem(item)
            add_button.setEnabled(result_list.currentItem() is not None)

        def on_current_changed() -> None:
            item = result_list.currentItem()
            if item is None:
                selected_label.setText("Выберите связь из списка")
                add_button.setEnabled(False)
                return
            selected_label.setText(item.text())
            add_button.setEnabled(True)

        def accept_relation() -> None:
            kind = str(type_combo.currentData() or "")
            if kind in {"repository", "wiki"}:
                url = url_edit.text().strip()
                if not url:
                    QMessageBox.warning(dialog, "Проверка", "Ссылка не должна быть пустой.")
                    return
                title = title_edit.text().strip()
                line = f"{title} | {url}" if title else url
                self._append_line(self.repository_links_edit if kind == "repository" else self.wiki_links_edit, line)
                self._refresh_preview_fields()
                dialog.accept()
                return
            item = result_list.currentItem()
            if item is None:
                QMessageBox.warning(dialog, "Проверка", "Выберите связь из списка.")
                return
            payload = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(payload, tuple) or len(payload) < 2:
                return
            self._apply_relation_payload(str(payload[0]), int(payload[1]))
            dialog.accept()

        type_combo.currentIndexChanged.connect(populate)
        search_edit.textChanged.connect(populate)
        result_list.currentItemChanged.connect(lambda _current, _previous: on_current_changed())
        result_list.itemDoubleClicked.connect(lambda _item: accept_relation())
        buttons.accepted.connect(accept_relation)
        populate()

        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def _relation_candidates(self, kind: str) -> list[tuple[int, str]]:
        if kind == "project":
            result = []
            for project in self._db.fetch_projects():
                if self._project and project.id == self._project.id:
                    continue
                result.append((project.id, f"{project.area} / {project.title}"))
            return result
        if kind == "task":
            return [(task.id, f"MN-{task.id} {task.title}") for task in self._db.fetch_tasks()]
        if kind == "map":
            return [(item.id, item.title) for item in self._db.fetch_maps()]
        if kind == "note":
            return [(item.id, item.title) for item in self._db.fetch_notes()]
        if kind == "object":
            return [(item.id, item.title) for item in self._db.fetch_objects()]
        return []

    def _apply_relation_payload(self, kind: str, item_id: int) -> None:
        if kind == "project":
            self._append_unique_int_line(self.related_projects_edit, item_id)
        elif kind == "task":
            self._append_unique_int_line(self.related_tasks_edit, item_id)
        elif kind == "map":
            self._set_combo_data(self.linked_map_edit, item_id)
        elif kind == "note":
            self._set_combo_data(self.linked_note_edit, item_id)
        elif kind == "object":
            self._set_combo_data(self.linked_object_edit, item_id)
        self._refresh_preview_fields()

    def _append_unique_int_line(self, edit: QPlainTextEdit, item_id: int) -> None:
        existing = set(self._parse_int_lines(edit.toPlainText(), "Связи"))
        if item_id in existing:
            return
        self._append_line(edit, str(item_id))

    @staticmethod
    def _set_combo_data(combo: QComboBox, item_id: int) -> None:
        index = combo.findData(item_id)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _add_repository_link_line(self) -> None:
        self._add_link_line(self.repository_links_edit, "Репозиторий")

    def _add_wiki_link_line(self) -> None:
        self._add_link_line(self.wiki_links_edit, "Wiki")

    def _add_display_property_line(self) -> None:
        if len([line for line in self.display_properties_edit.toPlainText().splitlines() if line.strip()]) >= 4:
            QMessageBox.warning(self, "Отображаемые свойства", "Можно добавить не более 4 отображаемых свойств.")
            return
        values = self._display_property_dialog()
        if values is not None:
            self._append_line(self.display_properties_edit, self._format_display_property_line(values))

    def _edit_display_property_line(self, line_index: Optional[int] = None) -> None:
        lines, current_line_index, line = self._current_line_info(self.display_properties_edit)
        if line_index is None:
            line_index = current_line_index
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if line_index < 0 or not line:
            return
        values = self._display_property_dialog(self._parse_display_property_line(line))
        if values is not None:
            self._replace_line(self.display_properties_edit, line_index, self._format_display_property_line(values))

    def _delete_display_property_line(self, line_index: Optional[int] = None) -> None:
        lines, current_line_index, line = self._current_line_info(self.display_properties_edit)
        if line_index is None:
            line_index = current_line_index
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if line_index >= 0 and line:
            self._remove_line(self.display_properties_edit, line_index)

    def _display_property_dialog(self, initial: Optional[dict[str, str]] = None) -> Optional[dict[str, str]]:
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование отображаемого свойства" if initial else "Создание отображаемого свойства")
        dialog.setObjectName("ProjectDisplayPropertyDialog")
        dialog.resize(860, 560)
        dialog.setMinimumSize(760, 500)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        hero_icon = QLabel()
        hero_icon.setPixmap(qta.icon("fa5s.link", color="#3478f6").pixmap(26, 26))
        header.addWidget(hero_icon, 0, Qt.AlignmentFlag.AlignTop)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_label = QLabel("Редактирование отображаемого свойства" if initial else "Создание отображаемого свойства")
        title_label.setObjectName("DisplayPropertyDialogTitle")
        subtitle_label = QLabel("Настройка отображаемых данных проекта")
        subtitle_label.setObjectName("DisplayPropertyDialogSubtitle")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header.addLayout(title_box, 1)
        preview_button = QPushButton("Предпросмотр")
        preview_button.setObjectName("DisplayPropertyDialogSecondaryButton")
        preview_button.setIcon(qta.icon("fa5s.eye", color=self._palette.text))
        close_button = QPushButton("Закрыть")
        close_button.setObjectName("DisplayPropertyDialogSecondaryButton")
        close_button.setIcon(qta.icon("fa5s.times", color=self._palette.text))
        close_button.clicked.connect(dialog.reject)
        header.addWidget(preview_button)
        header.addWidget(close_button)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        body.addLayout(left_column, 1)
        preview_card = QFrame()
        preview_card.setObjectName("DisplayPropertyPreviewCard")
        preview_card.setMinimumWidth(280)
        preview_card.setMaximumWidth(320)
        body.addWidget(preview_card)
        root.addLayout(body, 1)

        main_card = QFrame()
        main_card.setObjectName("DisplayPropertyCard")
        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)
        main_layout.addLayout(self._display_property_section_title("fa5s.clipboard-list", "Основное"))
        field_grid = QGridLayout()
        field_grid.setHorizontalSpacing(12)
        field_grid.setVerticalSpacing(6)
        name_edit = QLineEdit(str(initial.get("name") or "") if initial else "")
        name_edit.setPlaceholderText("WIKI")
        url_edit = QLineEdit(str(initial.get("url") or "") if initial else "")
        url_edit.setPlaceholderText("https://docs.example.com/kazantip")
        name_hint = QLabel("Короткое название свойства, отображается в блоке «Дополнительно».")
        name_hint.setObjectName("DisplayPropertyFieldHint")
        name_hint.setWordWrap(True)
        url_hint = QLabel("Ссылка открывается в браузере или может быть скопирована пользователем.")
        url_hint.setObjectName("DisplayPropertyFieldHint")
        url_hint.setWordWrap(True)
        field_grid.addLayout(self._display_property_field_label("Имя"), 0, 0)
        field_grid.addLayout(self._display_property_field_label("Ссылка"), 0, 1)
        field_grid.addWidget(name_edit, 1, 0)
        field_grid.addWidget(url_edit, 1, 1)
        field_grid.addWidget(name_hint, 2, 0)
        field_grid.addWidget(url_hint, 2, 1)
        main_layout.addLayout(field_grid)
        left_column.addWidget(main_card)

        mode_card = QFrame()
        mode_card.setObjectName("DisplayPropertyCard")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(14, 12, 14, 14)
        mode_layout.setSpacing(10)
        mode_layout.addLayout(self._display_property_section_title("fa5s.desktop", "Способ отображения"))
        mode_group = QButtonGroup(dialog)
        mode_group.setExclusive(True)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        name_link_radio, name_link_card = self._display_mode_card(
            "fa5s.link",
            "Имя со ссылкой внутри",
            "Отображается как имя свойства, внутри которого размещена гиперссылка.",
            "name_link",
        )
        url_text_radio, url_text_card = self._display_mode_card(
            "fa5s.link",
            "Текст ссылки",
            "Отображается как сама ссылка для открытия или копирования.",
            "url_text",
        )
        mode_group.addButton(name_link_radio)
        mode_group.addButton(url_text_radio)
        mode_row.addWidget(name_link_card)
        mode_row.addWidget(url_text_card)
        mode_layout.addLayout(mode_row)
        position_label = QLabel("Позиция в списке  ⓘ")
        position_label.setObjectName("DisplayPropertyFieldLabel")
        position_edit = QSpinBox()
        position_edit.setRange(1, 4)
        position_edit.setValue(1)
        mode_layout.addWidget(position_label)
        mode_layout.addWidget(position_edit)
        position_hint = QLabel("Отображаемые свойства выводятся после строки «Тип задач».")
        position_hint.setObjectName("DisplayPropertyFieldHint")
        mode_layout.addWidget(position_hint)
        selected_mode = (initial.get("display_mode") if initial else "") or "name_link"
        if selected_mode == "url_text":
            url_text_radio.setChecked(True)
        else:
            name_link_radio.setChecked(True)
        left_column.addWidget(mode_card)

        rules_card = QFrame()
        rules_card.setObjectName("DisplayPropertyCard")
        rules_layout = QVBoxLayout(rules_card)
        rules_layout.setContentsMargins(14, 12, 14, 14)
        rules_layout.setSpacing(8)
        rules_layout.addLayout(self._display_property_section_title("fa5s.shield-alt", "Ограничения и поведение"))
        for icon_name, color, text in (
            ("fa5s.info-circle", "#3478f6", "В одном проекте может быть не более 4 отображаемых свойств."),
            ("fa5s.list", "#3bd16f", "Каждый элемент выводится отдельной строкой в блоке «Дополнительно»."),
            ("fa5s.link", "#8a63d2", "Поддерживается открытие ссылки и копирование в буфер обмена."),
        ):
            rules_layout.addLayout(self._display_property_rule_row(icon_name, color, text))
        left_column.addWidget(rules_card)
        left_column.addStretch(1)

        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 12, 14, 14)
        preview_layout.setSpacing(10)
        preview_layout.addLayout(self._display_property_section_title("fa5s.eye", "Предпросмотр"))
        preview_caption = QLabel("Как это выглядит в задаче")
        preview_caption.setObjectName("DisplayPropertyPreviewCaption")
        preview_layout.addWidget(preview_caption)
        task_type_row = QHBoxLayout()
        task_type_label = QLabel("Тип задач:")
        task_type_label.setObjectName("DisplayPropertyPreviewLabel")
        task_type_badge = QLabel("РАЗРАБОТКА · DEV")
        task_type_badge.setObjectName("DisplayPropertyPreviewBadge")
        task_type_row.addWidget(task_type_label)
        task_type_row.addWidget(task_type_badge)
        task_type_row.addStretch(1)
        preview_layout.addLayout(task_type_row)
        preview_layout.addWidget(self._display_property_separator())
        props_title = QLabel("Отображаемые свойства")
        props_title.setObjectName("DisplayPropertyPreviewTitle")
        preview_layout.addWidget(props_title)
        property_row = QHBoxLayout()
        property_name = QLabel("WIKI:")
        property_name.setObjectName("DisplayPropertyPreviewLabel")
        property_value = QLabel()
        property_value.setObjectName("DisplayPropertyPreviewLink")
        property_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        property_row.addWidget(property_name)
        property_row.addWidget(property_value, 1)
        preview_layout.addLayout(property_row)
        repo_row = QHBoxLayout()
        repo_name = QLabel("REPO:")
        repo_name.setObjectName("DisplayPropertyPreviewLabel")
        repo_value = QLabel("https://github.com/lexflame/mindnavigator")
        repo_value.setObjectName("DisplayPropertyPreviewUrl")
        repo_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        repo_row.addWidget(repo_name)
        repo_row.addWidget(repo_value, 1)
        preview_layout.addLayout(repo_row)
        preview_layout.addWidget(self._display_property_separator())
        about_row = QHBoxLayout()
        about_icon = QLabel()
        about_icon.setPixmap(qta.icon("fa5s.info-circle", color=self._palette.text).pixmap(22, 22))
        about_title = QLabel("О свойстве")
        about_title.setObjectName("DisplayPropertyPreviewTitle")
        about_row.addWidget(about_icon)
        about_row.addWidget(about_title)
        about_row.addStretch(1)
        preview_layout.addLayout(about_row)
        about_text = QLabel(
            "Свойство отображается в блоке «Дополнительно» после строки «Тип задач». "
            "Элемент может открывать ссылку в браузере или позволять копирование."
        )
        about_text.setObjectName("DisplayPropertyPreviewText")
        about_text.setWordWrap(True)
        preview_layout.addWidget(about_text)
        preview_layout.addStretch(1)
        preview_button.clicked.connect(lambda: preview_card.setFocus(Qt.FocusReason.OtherFocusReason))

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 0, 0)
        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("DisplayPropertyDialogSecondaryButton")
        cancel_button.setIcon(qta.icon("fa5s.times", color=self._palette.text))
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Сохранить")
        save_button.setObjectName("DisplayPropertyDialogPrimaryButton")
        save_button.setIcon(qta.icon("fa5s.save", color=self._palette.selection_text))
        save_more_button = QPushButton("Сохранить и добавить ещё")
        save_more_button.setObjectName("DisplayPropertyDialogSecondaryButton")
        save_more_button.setIcon(qta.icon("fa5s.plus-circle", color=self._palette.text))
        save_button.clicked.connect(dialog.accept)
        save_more_button.clicked.connect(dialog.accept)
        footer.addWidget(cancel_button)
        footer.addStretch(1)
        footer.addWidget(save_button)
        footer.addWidget(save_more_button)
        root.addLayout(footer)

        def selected_mode_value() -> str:
            return "url_text" if url_text_radio.isChecked() else "name_link"

        def update_preview() -> None:
            name = "".join(name_edit.text().strip().upper().split()) or "WIKI"
            url = url_edit.text().strip() or "https://docs.example.com/kazantip"
            property_name.setText(f"{name}:")
            if selected_mode_value() == "url_text":
                property_value.setObjectName("DisplayPropertyPreviewUrl")
                property_value.setText(url)
            else:
                property_value.setObjectName("DisplayPropertyPreviewLink")
                property_value.setText(f"🔗  {name}")
            property_value.style().unpolish(property_value)
            property_value.style().polish(property_value)

        name_edit.textChanged.connect(update_preview)
        url_edit.textChanged.connect(update_preview)
        name_link_radio.toggled.connect(update_preview)
        url_text_radio.toggled.connect(update_preview)
        update_preview()
        self._apply_display_property_dialog_style(dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        name = "".join(name_edit.text().strip().upper().split())
        url = url_edit.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "Проверка", "Имя и ссылка отображаемого свойства обязательны.")
            return None
        return {"name": name, "url": url, "display_mode": selected_mode_value()}

    @staticmethod
    def _format_display_property_line(values: dict[str, str]) -> str:
        return f"{values.get('name') or ''} | {values.get('url') or ''} | {values.get('display_mode') or 'name_link'}"

    @staticmethod
    def _parse_display_property_line(line: str) -> dict[str, str]:
        parts = [part.strip() for part in (line or "").split("|")]
        return {
            "name": "".join((parts[0] if parts else "").strip().upper().split()),
            "url": parts[1] if len(parts) > 1 else "",
            "display_mode": parts[2] if len(parts) > 2 and parts[2] in {"name_link", "url_text"} else "name_link",
        }

    def _add_link_line(self, edit: QPlainTextEdit, title: str) -> None:
        values = self._link_dialog(title)
        if values is not None:
            self._append_line(edit, self._format_link_line(values))

    def _edit_link_line(self, edit: QPlainTextEdit, title: str, line_index: int) -> None:
        lines = edit.toPlainText().splitlines()
        line = lines[line_index].strip() if 0 <= line_index < len(lines) else ""
        if not line:
            return
        values = self._link_dialog(title, self._parse_link_line(line))
        if values is not None:
            self._replace_line(edit, line_index, self._format_link_line(values))

    def _link_dialog(self, title: str, initial: Optional[dict[str, str]] = None) -> Optional[dict[str, str]]:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setObjectName("ProjectCompactLinkDialog")
        dialog.setFixedSize(550, 220)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        title_edit = QLineEdit(str(initial.get("title") or "") if initial else "")
        url_edit = QLineEdit(str(initial.get("url") or "") if initial else "")
        title_edit.setPlaceholderText("Короткое имя")
        url_edit.setPlaceholderText("https://example.com или путь")
        form.addRow("Текст", title_edit)
        form.addRow("Ссылка", url_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(dialog)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        self._apply_child_dialog_style(dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        url = url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Проверка", "Ссылка не должна быть пустой.")
            return None
        link_title = title_edit.text().strip()
        return {"title": link_title, "url": url}

    @staticmethod
    def _format_link_line(values: dict[str, str]) -> str:
        title = (values.get("title") or "").strip()
        url = (values.get("url") or "").strip()
        return f"{title} | {url}" if title else url

    @staticmethod
    def _parse_link_line(line: str) -> dict[str, str]:
        line = (line or "").strip()
        if "|" in line:
            title, url = [part.strip() for part in line.split("|", 1)]
        else:
            title, url = "", line
        return {"title": title, "url": url}

    def _load_project_properties(self, project_id: int) -> None:
        task_type_lines = []
        for item in self._db.fetch_project_task_types(project_id, include_inactive=True):
            task_type_lines.append(self._format_task_type_line({
                "title": item.title,
                "value": item.value,
                "color_marker": item.color_marker,
                "theme_marker": item.theme_marker,
                "priority": item.priority,
                "importance": item.importance,
                "is_plan_task": item.is_plan_task,
                "concept_board_id": item.concept_board_id,
                "active": item.active,
            }))
        self.task_types_edit.setPlainText("\n".join(task_type_lines))
        self.related_projects_edit.setPlainText(
            "\n".join(str(item.related_project_id) for item in self._db.fetch_project_related_projects(project_id))
        )
        self.related_tasks_edit.setPlainText(
            "\n".join(str(item.task_id) for item in self._db.fetch_project_related_tasks(project_id))
        )
        self.repository_links_edit.setPlainText(self._format_links(self._db.fetch_project_repository_links(project_id)))
        self.wiki_links_edit.setPlainText(self._format_links(self._db.fetch_project_wiki_links(project_id)))
        fetch_display = getattr(self._db, "fetch_project_display_properties", None)
        if callable(fetch_display):
            self.display_properties_edit.setPlainText(
                "\n".join(self._format_display_property_line({
                    "name": item.name,
                    "url": item.url,
                    "display_mode": item.display_mode,
                }) for item in fetch_display(project_id))
            )
        self._refresh_inline_property_lists()

    @staticmethod
    def _project_reflect_setting_key(project_id: int) -> str:
        return f"{PROJECT_REFLECT_SETTING_PREFIX}:{int(project_id)}"

    def _load_project_reflect_settings(self, project_id: int) -> None:
        raw_value = self._db.get_setting(self._project_reflect_setting_key(project_id), "[]")
        try:
            values = json.loads(raw_value)
        except json.JSONDecodeError:
            values = []
        enabled_keys = {str(value) for value in values if str(value) in PROJECT_REFLECT_KEYS}
        self.reflect_repository_catalog_edit.setChecked(PROJECT_REFLECT_REPOSITORY_CATALOG in enabled_keys)
        self.reflect_repository_links_edit.setChecked(PROJECT_REFLECT_REPOSITORY_LINKS in enabled_keys)
        self.reflect_wiki_links_edit.setChecked(PROJECT_REFLECT_WIKI_LINKS in enabled_keys)
        self.reflect_linked_map_edit.setChecked(PROJECT_REFLECT_LINKED_MAP in enabled_keys)
        self.reflect_linked_note_edit.setChecked(PROJECT_REFLECT_LINKED_NOTE in enabled_keys)
        self.reflect_linked_object_edit.setChecked(PROJECT_REFLECT_LINKED_OBJECT in enabled_keys)

    def _save_project_reflect_settings(self, project_id: int) -> None:
        values = []
        if self.reflect_repository_catalog_edit.isChecked():
            values.append(PROJECT_REFLECT_REPOSITORY_CATALOG)
        if self.reflect_repository_links_edit.isChecked():
            values.append(PROJECT_REFLECT_REPOSITORY_LINKS)
        if self.reflect_wiki_links_edit.isChecked():
            values.append(PROJECT_REFLECT_WIKI_LINKS)
        if self.reflect_linked_map_edit.isChecked():
            values.append(PROJECT_REFLECT_LINKED_MAP)
        if self.reflect_linked_note_edit.isChecked():
            values.append(PROJECT_REFLECT_LINKED_NOTE)
        if self.reflect_linked_object_edit.isChecked():
            values.append(PROJECT_REFLECT_LINKED_OBJECT)
        self._db.set_setting(
            self._project_reflect_setting_key(project_id),
            json.dumps(values, ensure_ascii=False),
        )

    @staticmethod
    def _format_links(links) -> str:
        return "\n".join(f"{item.title} | {item.url}" if item.title else item.url for item in links)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.currentText())
            validate_title(self.title_edit.text(), field_name="Название проекта")
            normalize_priority(self.priority_edit.currentText())
            self._parse_project_task_types()
            self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты")
            self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи")
            self._parse_links(self.repository_links_edit.toPlainText())
            self._parse_links(self.wiki_links_edit.toPlainText())
            self._parse_display_properties()
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return

        self.accept()

    def apply_project_properties(self, project_id: int) -> None:
        self._db.replace_project_task_types(project_id, self._parse_project_task_types())
        self._db.replace_project_related_projects(
            project_id,
            self._parse_int_lines(self.related_projects_edit.toPlainText(), "Связанные проекты"),
        )
        self._db.replace_project_related_tasks(
            project_id,
            self._parse_int_lines(self.related_tasks_edit.toPlainText(), "Связанные задачи"),
        )
        self._db.replace_project_repository_links(project_id, self._parse_links(self.repository_links_edit.toPlainText()))
        self._db.replace_project_wiki_links(project_id, self._parse_links(self.wiki_links_edit.toPlainText()))
        replace_display = getattr(self._db, "replace_project_display_properties", None)
        if callable(replace_display):
            replace_display(project_id, self._parse_display_properties())
        self._save_project_reflect_settings(project_id)

    def _parse_project_task_types(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        seen: set[str] = set()
        for raw_line in self.task_types_edit.toPlainText().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            values = self._parse_task_type_line(line)
            title = str(values.get("title") or "")
            if not title:
                raise ValueError("Название типа задач не должно быть пустым.")
            if title in seen:
                raise ValueError(f"Дублирующий тип задач: {title}")
            seen.add(title)
            result.append(
                {
                    "title": title,
                    "value": str(values.get("value") or title),
                    "color_marker": str(values.get("color_marker") or ""),
                    "theme_marker": str(values.get("theme_marker") or ""),
                    "priority": str(values.get("priority") or ""),
                    "importance": int(values.get("importance") or 3),
                    "is_plan_task": bool(values.get("is_plan_task", False)),
                    "concept_board_id": values.get("concept_board_id"),
                    "active": bool(values.get("active", True)),
                }
            )
        return result

    def _parse_display_properties(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        seen: set[str] = set()
        for raw_line in self.display_properties_edit.toPlainText().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            values = self._parse_display_property_line(line)
            name = str(values.get("name") or "")
            url = str(values.get("url") or "")
            if not name:
                raise ValueError("Имя отображаемого свойства не должно быть пустым.")
            if not url:
                raise ValueError("Ссылка отображаемого свойства не должна быть пустой.")
            if name in seen:
                raise ValueError(f"Дублирующее отображаемое свойство: {name}")
            seen.add(name)
            result.append(values)
        if len(result) > 4:
            raise ValueError("В проекте может быть не более 4 отображаемых свойств.")
        return result

    @staticmethod
    def _parse_int_lines(text: str, field_name: str) -> list[int]:
        result: list[int] = []
        seen: set[int] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                item_id = int(line)
            except ValueError as exc:
                raise ValueError(f"{field_name}: ожидается числовой ID, получено {line!r}.") from exc
            if item_id not in seen:
                seen.add(item_id)
                result.append(item_id)
        return result

    @staticmethod
    def _parse_links(text: str) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "|" in line:
                title, url = [part.strip() for part in line.split("|", 1)]
            else:
                title, url = "", line
            if not url:
                raise ValueError("Ссылка repository/wiki не должна быть пустой.")
            links.append({"title": title, "url": url})
        return links

    def values(self) -> dict:
        """Возвращает значения формы проекта."""
        qd = self.updated_edit.date()
        return {
            "area": self.area_edit.currentText().strip(),
            "title": self.title_edit.text().strip(),
            "updated": date(qd.year(), qd.month(), qd.day()),
            "priority": self.priority_edit.currentText().strip() or "Medium",
            "parent_project_id": self.parent_project_edit.currentData(),
            "default_task_priority": self.default_task_priority_edit.currentData() or "",
            "force_recurrence_kind": self.force_recurrence_kind_edit.currentData() or "",
            "linked_map_id": self.linked_map_edit.currentData(),
            "linked_note_id": self.linked_note_edit.currentData(),
            "linked_object_id": self.linked_object_edit.currentData(),
            "marker_color": self.marker_color_edit.currentData() or "",
            "marker_theme": self.marker_theme_edit.currentData() or "",
            "repository_catalog": self.repository_catalog_edit.text().strip(),
            "archived": self.archived_edit.isChecked(),
        }

__all__ = ["ProjectEditDialog"]
