# Dialog Remaster Inventory (QDialog)

## 1) Summary
- Total dialog classes (QDialog subclasses): **15**.
- Total dialog call-sites (instantiation + show): **33**.
- Base helpers/patterns detected:
  - `mindnavigator/ui/modals.py:47` -> `exec_with_overlay(dialog, parent)` wraps `dialog.exec()` with dimmed `ModalOverlay` (`mindnavigator/ui/modals.py:18`).
  - `mindnavigator/ui/modals.py:56` -> reusable `ConfirmDialog(QDialog)` used across Tasks/Projects/Ideas/Settings.
  - Multiple inline `QDialog(self)` info/view dialogs with local styling/object names in workspace modules.

## 2) Table: Dialog classes
| Dialog class name | File path | Parent | How it is shown (exec/open/show) | Notes (flags/titlebar/overlay hints) |
|---|---|---|---|---|
| `MapEditDialog` | `mindnavigator/workspaces/maps_workspace.py:412` | `QDialog` | `exec` (`mindnavigator/workspaces/maps_workspace.py:3568`) | `setMinimumWidth(460)`, `setMinimumHeight(400)`, styled dialog. |
| `MapImagePreviewDialog` | `mindnavigator/workspaces/maps_workspace.py:638` | `QDialog` | `exec` (`mindnavigator/workspaces/maps_workspace.py:908`) | Fullscreen via `setWindowState(...|Qt.WindowFullScreen)` (`mindnavigator/workspaces/maps_workspace.py:682`). |
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:822` | `QDialog` | `exec_with_overlay` (`mindnavigator/workspaces/tasks_workspace.py:1338`, `mindnavigator/workspaces/tasks_workspace.py:1980`) | Fullscreen via `setWindowState(...|Qt.WindowFullScreen)` (`mindnavigator/workspaces/tasks_workspace.py:839`). |
| `TaskDetailsDialog` | `mindnavigator/workspaces/tasks_workspace.py:929` | `QDialog` | `exec_with_overlay` (`mindnavigator/workspaces/tasks_workspace.py:2515`) | `setMinimumWidth(760)`, `setMinimumHeight(680)`; owns inline attachment/info dialogs. |
| `TaskEditDialog` | `mindnavigator/workspaces/tasks_workspace.py:1341` | `QDialog` | `exec_with_overlay` (`mindnavigator/workspaces/tasks_workspace.py:2487`) | `setMinimumWidth(460)`, `setMinimumHeight(420)`; owns inline attachment/info dialogs. |
| `ImagePreviewDialog` | `mindnavigator/workspaces/files_workspace.py:163` | `QDialog` | `showFullScreen` + `exec` (`mindnavigator/workspaces/files_workspace.py:868`, `mindnavigator/workspaces/files_workspace.py:869`) | Also has `setMinimumSize(800, 600)`. |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:316` | `QDialog` | `exec` (`mindnavigator/workspaces/objects_workspace.py:935`, `mindnavigator/workspaces/objects_workspace.py:954`) | `setMinimumWidth(520)`. |
| `CloudDocPickerDialog` | `mindnavigator/workspaces/objects_workspace.py:412` | `QDialog` | `exec` (`mindnavigator/workspaces/objects_workspace.py:400`) | `setMinimumSize(520, 420)`. |
| `CloudImagePickerDialog` | `mindnavigator/workspaces/objects_workspace.py:482` | `QDialog` | `exec` (`mindnavigator/workspaces/objects_workspace.py:992`) | `setMinimumSize(620, 460)`. |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:730` | `QDialog` | `exec_with_overlay` (`mindnavigator/workspaces/projects_workspace.py:691`), direct `exec` (`mindnavigator/workspaces/projects_workspace.py:1104`) | `setMinimumWidth(460)`, `setMinimumHeight(300)`. |
| `ProjectAreaEditDialog` | `mindnavigator/workspaces/projects_workspace.py:862` | `QDialog` | `exec_with_overlay` (`mindnavigator/workspaces/projects_workspace.py:668`) | `setMinimumWidth(420)`. |
| `ConfirmDialog` | `mindnavigator/ui/modals.py:56` | `QDialog` | Via `exec_with_overlay` in call-sites | Shared confirm modal; `setMinimumWidth(420)`. |
| `MapLabelEditDialog` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:528` | `QDialog` | `exec` (`mindnavigator/workspaces/maps_workspace.py:1836`) | `resize(1100,760)`, `setMinimumSize(840,520)`, dynamic fit/center logic (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1135`). |
| `EntityPickerDialog` | `mindnavigator/ui/dialogs/entity_picker_dialog.py:38` | `QDialog` | `exec` (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1509`) | `Qt.Popup | Qt.FramelessWindowHint`, anchor-based `move(...)`. |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/attach_file_select_nav.py:39` | `QDialog` | `exec` (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1381`, `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1521`) | `resize(900,620)`, `setMinimumSize(720,520)`. |

## 3) Table: Dialog call-sites
| Dialog class (or QDialog) | File path + function/method name | Show method (exec/open/show) | Parent passed? | Local geometry/positioning code present? | Notes |
|---|---|---|---|---|---|
| `MapImagePreviewDialog` | `mindnavigator/workspaces/maps_workspace.py:888` `_open_image_attachment` | `exec` | yes (`self`) | no | Fullscreen behavior is in dialog class. |
| `QDialog` | `mindnavigator/workspaces/maps_workspace.py:910` `_open_attachment_view` | `exec` | yes (`self`) | no | Inline attachment info dialog; title changes by entity kind. |
| `MapLabelEditDialog` | `mindnavigator/workspaces/maps_workspace.py:1733` `_edit_marker` | `exec` | yes (`parent=self`) | no | Marker edit workflow. |
| `QDialog` | `mindnavigator/workspaces/maps_workspace.py:1862` `_view_marker` | `exec` | yes (`self`) | yes (`resize`, `setMinimumSize` at `mindnavigator/workspaces/maps_workspace.py:1867`) | Inline marker view dialog. |
| `MapEditDialog` | `mindnavigator/workspaces/maps_workspace.py:3554` `_on_edit_map` | `exec` | yes (`parent=self`) | no | Map edit entry point from list. |
| `QDialog` | `mindnavigator/workspaces/tasks_workspace.py:1271` `_open_info_dialog` (`TaskDetailsDialog`) | `exec_with_overlay` | yes (`self`) | no | Inline info dialog for linked entities/files. |
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:1319` `_open_image_preview` (`TaskDetailsDialog`) | `exec_with_overlay` | yes (`self`) | no | Attachment image preview. |
| `QDialog` | `mindnavigator/workspaces/tasks_workspace.py:1733` `_open_attachment_dialog` (`TaskEditDialog`) | `exec` | yes (`self`) | no | Add-attachment chooser inline dialog. |
| `QDialog` | `mindnavigator/workspaces/tasks_workspace.py:1913` `_open_info_dialog` (`TaskEditDialog`) | `exec_with_overlay` | yes (`self`) | no | Inline info dialog duplicate pattern. |
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:1961` `_open_image_preview` (`TaskEditDialog`) | `exec_with_overlay` | yes (`self`) | no | Attachment image preview. |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2347` `editorEvent` | `exec_with_overlay` | unknown (`parent=option.widget or None`) | no | Confirm before marking task as done. |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2418` `_show_row_menu` | `exec_with_overlay` | unknown (`parent=menu.parentWidget() or None`) | no | Confirm task deletion. |
| `TaskEditDialog` | `mindnavigator/workspaces/tasks_workspace.py:2475` `_edit_task` | `exec_with_overlay` | unknown (`self.parent()` may be widget/None) | no | Row-level task edit. |
| `TaskDetailsDialog` | `mindnavigator/workspaces/tasks_workspace.py:2506` `_open_task_view` | `exec_with_overlay` | unknown (`self.parent()` may be widget/None) | no | Row-level read-only details. |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2913` `_delete_selected_task` | `exec_with_overlay` | yes (`self`) | no | Toolbar/selection delete flow. |
| `ImagePreviewDialog` | `mindnavigator/workspaces/files_workspace.py:846` `_open_image_preview` | `showFullScreen` + `exec` | yes (`self`) | yes (`showFullScreen` at `mindnavigator/workspaces/files_workspace.py:868`) | Fullscreen preview of images in current folder. |
| `CloudDocPickerDialog` | `mindnavigator/workspaces/objects_workspace.py:398` `_import_description` (`ObjectEditDialog`) | `exec` | yes (`self`) | no | Nested picker from object edit form. |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:933` `_add_object` | `exec` | yes (`self`) | no | Create object dialog. |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:946` `_edit_current_object` | `exec` | yes (`self`) | no | Edit selected object. |
| `CloudImagePickerDialog` | `mindnavigator/workspaces/objects_workspace.py:988` `_attach_images` | `exec` | yes (`self`) | no | Multi-select image attach flow. |
| `QDialog` | `mindnavigator/workspaces/objects_workspace.py:1084` `_preview_image` | `exec` | yes (`self`) | yes (`setMinimumSize` at `mindnavigator/workspaces/objects_workspace.py:1096`) | Inline simple image preview. |
| `ConfirmDialog` | `mindnavigator/workspaces/projects_workspace.py:546` `_show_row_menu` | `exec_with_overlay` | unknown (`parent=menu.parentWidget() or None`) | no | Confirm project deletion. |
| `ConfirmDialog` | `mindnavigator/workspaces/projects_workspace.py:604` `_show_area_menu` | `exec_with_overlay` | unknown (`parent=menu.parentWidget() or None`) | no | Confirm area deletion. |
| `ProjectAreaEditDialog` | `mindnavigator/workspaces/projects_workspace.py:664` `_edit_area` | `exec_with_overlay` | unknown (`self.parent()` may be widget/None) | no | Area rename/edit. |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:679` `_edit_project` | `exec_with_overlay` | unknown (`self.parent()` may be widget/None) | no | Project edit flow. |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:1101` `_on_create_project` | `exec` | yes (`self`) | no | Project creation flow (without overlay helper). |
| `ConfirmDialog` | `mindnavigator/workspaces/ideas_workspace.py:619` `_maybe_save_changes` | `exec_with_overlay` | yes (`self`) | no | Prompt before discarding unsaved edits. |
| `ConfirmDialog` | `mindnavigator/workspaces/ideas_workspace.py:685` `_delete_selected` | `exec_with_overlay` | yes (`self`) | no | Confirm idea deletion. |
| `ConfirmDialog` | `mindnavigator/workspaces/settings_workspace.py:535` `_restore_selected_backup` | `exec_with_overlay` | yes (`self`) | no | Confirm destructive restore operation. |
| `ConfirmDialog` | `mindnavigator/workspaces/settings_workspace.py:595` `_delete_selected_backup` | `exec_with_overlay` | yes (`self`) | no | Confirm backup file deletion. |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1378` `_choose_image` | `exec` | yes (`self`) | no | Pick cloud file for marker image. |
| `EntityPickerDialog` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1480` `_open_picker` | `exec` | yes (`self`) | no | Popup-style entity selector; anchor widget provided. |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1518` `_open_file_picker` | `exec` | yes (`self`) | no | Pick linked file for map marker relations. |

## 4) Special cases
- Already frameless/custom-titlebar-like:
  - `EntityPickerDialog` uses `Qt.Popup | Qt.FramelessWindowHint` (`mindnavigator/ui/dialogs/entity_picker_dialog.py:51`) and anchor positioning (`mindnavigator/ui/dialogs/entity_picker_dialog.py:144`).
- Existing overlay/backdrop implementation:
  - `ModalOverlay` + `exec_with_overlay` (`mindnavigator/ui/modals.py:18`, `mindnavigator/ui/modals.py:47`) is a reusable dimmed modal pattern.
- Fullscreen dialog behaviors that should be preserved:
  - `MapImagePreviewDialog` (`mindnavigator/workspaces/maps_workspace.py:682`).
  - `TaskImagePreviewDialog` (`mindnavigator/workspaces/tasks_workspace.py:839`).
  - `ImagePreviewDialog` call-site forces fullscreen before exec (`mindnavigator/workspaces/files_workspace.py:868`).
- Unique size/position behaviors:
  - `MapLabelEditDialog` has screen-fit + centering logic and dynamic max/min size adjustments (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1135`).
  - Inline marker view dialog in maps workspace uses explicit starting size + minimum size (`mindnavigator/workspaces/maps_workspace.py:1867`).
- Mixed modal-launch pattern in same workspace:
  - `ProjectEditDialog` is launched both with overlay helper and plain `exec` (`mindnavigator/workspaces/projects_workspace.py:691`, `mindnavigator/workspaces/projects_workspace.py:1104`).
