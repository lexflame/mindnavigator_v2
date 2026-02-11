# Dialog Remaster Inventory (mindnavigator_v2)

## 1) Summary

- Total dialogs found: **21**
  - **15** QDialog subclasses
  - **6** ad-hoc `QDialog(self)` constructions
- Total dialog call-sites found (instantiation + show): **33**
- Existing base helpers/patterns:
  - `mindnavigator/ui/modals.py:47` - `exec_with_overlay(dialog, parent)` wraps dialog execution with backdrop overlay.
  - `mindnavigator/ui/modals.py:18` - `ModalOverlay(QFrame)` keeps dim overlay synced with parent geometry.
  - `ConfirmDialog` is the shared confirmation dialog pattern used in multiple workspaces.

## 2) Table: Dialog classes

| Dialog class name | File path | Parent | How it is shown (known) | Notes (flags/titlebar/overlay hints) |
|---|---|---|---|---|
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:822` | `QDialog` | `exec_with_overlay(...)` from task attachment/image flows | Fullscreen via `setWindowState(... | Qt.WindowFullScreen)` (`mindnavigator/workspaces/tasks_workspace.py:839`) |
| `TaskDetailsDialog` | `mindnavigator/workspaces/tasks_workspace.py:929` | `QDialog` | `exec_with_overlay(...)` | `setMinimumWidth(760)`, `setMinimumHeight(680)` |
| `TaskEditDialog` | `mindnavigator/workspaces/tasks_workspace.py:1341` | `QDialog` | `exec_with_overlay(...)` | `setMinimumWidth(460)`, `setMinimumHeight(420)` |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:730` | `QDialog` | `exec_with_overlay(...)`, direct `dialog.exec()` for create | `setMinimumWidth(460)`, `setMinimumHeight(300)` |
| `ProjectAreaEditDialog` | `mindnavigator/workspaces/projects_workspace.py:862` | `QDialog` | `exec_with_overlay(...)` | `setMinimumWidth(420)` |
| `ConfirmDialog` | `mindnavigator/ui/modals.py:56` | `QDialog` | `exec_with_overlay(...)` across workspaces | Shared app-styled confirm dialog, `setMinimumWidth(420)` |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:316` | `QDialog` | direct `dialog.exec()` | `setMinimumWidth(520)` |
| `CloudDocPickerDialog` | `mindnavigator/workspaces/objects_workspace.py:412` | `QDialog` | direct `dialog.exec()` | `setMinimumSize(520, 420)` |
| `CloudImagePickerDialog` | `mindnavigator/workspaces/objects_workspace.py:482` | `QDialog` | direct `dialog.exec()` | `setMinimumSize(620, 460)` |
| `MapEditDialog` | `mindnavigator/workspaces/maps_workspace.py:412` | `QDialog` | direct `dialog.exec()` | `setMinimumWidth(460)`, `setMinimumHeight(400)` |
| `MapImagePreviewDialog` | `mindnavigator/workspaces/maps_workspace.py:638` | `QDialog` | direct `dialog.exec()` | Fullscreen via `setWindowState(... | Qt.WindowFullScreen)` (`mindnavigator/workspaces/maps_workspace.py:682`) |
| `ImagePreviewDialog` | `mindnavigator/workspaces/files_workspace.py:163` | `QDialog` | `showFullScreen()` + `dialog.exec()` | `setMinimumSize(800, 600)` |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/attach_file_select_nav.py:39` | `QDialog` | direct `dialog.exec()` | `resize(900, 620)`, `setMinimumSize(720, 520)` |
| `MapLabelEditDialog` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:528` | `QDialog` | direct `dialog.exec()` | `resize(1100, 760)`, `setMinimumSize(840, 520)`, dynamic fit/centering via `_fit_to_screen()` (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1135`) |
| `EntityPickerDialog` | `mindnavigator/ui/dialogs/entity_picker_dialog.py:38` | `QDialog` | direct `dialog.exec()` | Frameless popup: `Qt.Popup | Qt.FramelessWindowHint` (`mindnavigator/ui/dialogs/entity_picker_dialog.py:51`), anchored `move(anchor_pos)` |
| `TaskAttachmentInfoDialog` (ad-hoc) | `mindnavigator/workspaces/tasks_workspace.py:1272` and `mindnavigator/workspaces/tasks_workspace.py:1914` | `QDialog` | one path via `exec_with_overlay(...)` | `setObjectName("TaskAttachmentInfoDialog")`, form-style info dialog |
| `TaskAttachmentDialog` (ad-hoc) | `mindnavigator/workspaces/tasks_workspace.py:1735` | `QDialog` | direct `dialog.exec()` | `setObjectName("TaskAttachmentDialog")`, attachment chooser |
| `MapAttachmentDialog` (ad-hoc) | `mindnavigator/workspaces/maps_workspace.py:927` | `QDialog` | direct `dialog.exec()` | `setObjectName("MapAttachmentDialog")` |
| `MapLabelViewDialog` (ad-hoc) | `mindnavigator/workspaces/maps_workspace.py:1864` | `QDialog` | direct `dialog.exec()` | `resize(980, 680)`, `setMinimumSize(760, 520)` |
| image preview ad-hoc (`QDialog`) | `mindnavigator/workspaces/objects_workspace.py:1094` | `QDialog` | direct `dialog.exec()` | `setMinimumSize(800, 600)` |

## 3) Table: Dialog call-sites

| Dialog class (or QDialog) | File path + function/method name | Show method | Parent passed? | Local geometry/positioning code present? | Notes |
|---|---|---|---|---|---|
| `QDialog` (`TaskAttachmentInfoDialog`) | `mindnavigator/workspaces/tasks_workspace.py:1271` (`TaskDetailsDialog._open_info_dialog`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/tasks_workspace.py:1307` | yes | no | info/details dialog |
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:1319` (`TaskDetailsDialog._open_image_preview`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/tasks_workspace.py:1338` | yes | no | image gallery preview |
| `QDialog` (`TaskAttachmentDialog`) | `mindnavigator/workspaces/tasks_workspace.py:1733` (`TaskEditDialog._open_attachment_dialog`) | `dialog.exec()` at `mindnavigator/workspaces/tasks_workspace.py:1823` | yes | no | add attachment flow |
| `QDialog` (`TaskAttachmentInfoDialog`) | `mindnavigator/workspaces/tasks_workspace.py:1913` (`TaskEditDialog._open_info_dialog`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/tasks_workspace.py:1949` | yes | no | file/entity metadata |
| `TaskImagePreviewDialog` | `mindnavigator/workspaces/tasks_workspace.py:1961` (`TaskEditDialog._open_image_preview`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/tasks_workspace.py:1980` | yes | no | image gallery preview |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2347` (`TaskItemDelegate.editorEvent`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/tasks_workspace.py:2406` | yes | no | confirm task completion |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2418` (`TaskItemDelegate._show_row_menu`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/tasks_workspace.py:2468` | yes | no | confirm delete |
| `TaskEditDialog` | `mindnavigator/workspaces/tasks_workspace.py:2475` (`TaskItemDelegate._edit_task`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/tasks_workspace.py:2487` | yes | no | edit selected task |
| `TaskDetailsDialog` | `mindnavigator/workspaces/tasks_workspace.py:2506` (`TaskItemDelegate._open_task_view`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/tasks_workspace.py:2515` | yes | no | view task details |
| `ConfirmDialog` | `mindnavigator/workspaces/tasks_workspace.py:2913` (`TasksWorkspace._delete_selected_task`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/tasks_workspace.py:2925` | yes | no | confirm delete via toolbar/selection |
| `ConfirmDialog` | `mindnavigator/workspaces/projects_workspace.py:546` (`ProjectsDelegate._show_row_menu`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/projects_workspace.py:596` | yes | no | confirm project delete |
| `ConfirmDialog` | `mindnavigator/workspaces/projects_workspace.py:604` (`ProjectsDelegate._show_area_menu`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/projects_workspace.py:657` | yes | no | confirm area delete |
| `ProjectAreaEditDialog` | `mindnavigator/workspaces/projects_workspace.py:664` (`ProjectsDelegate._edit_area`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/projects_workspace.py:668` | yes | no | rename area |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:679` (`ProjectsDelegate._edit_project`) | `exec_with_overlay(dialog, parent)` at `mindnavigator/workspaces/projects_workspace.py:691` | yes | no | edit project |
| `ProjectEditDialog` | `mindnavigator/workspaces/projects_workspace.py:1101` (`ProjectsWorkspace._on_create_project`) | `dialog.exec()` at `mindnavigator/workspaces/projects_workspace.py:1104` | yes | no | create project |
| `ConfirmDialog` | `mindnavigator/workspaces/ideas_workspace.py:619` (`IdeasWorkspace._maybe_save_changes`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/ideas_workspace.py:629` | yes | no | save-unsaved-changes confirmation |
| `ConfirmDialog` | `mindnavigator/workspaces/ideas_workspace.py:685` (`IdeasWorkspace._delete_selected`) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/ideas_workspace.py:696` | yes | no | confirm idea delete |
| `ConfirmDialog` | `mindnavigator/workspaces/settings_workspace.py:543` (`SettingsWorkspace` backup restore action) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/settings_workspace.py:550` | yes | no | confirm restore backup |
| `ConfirmDialog` | `mindnavigator/workspaces/settings_workspace.py:602` (`SettingsWorkspace` backup delete action) | `exec_with_overlay(dialog, self)` at `mindnavigator/workspaces/settings_workspace.py:609` | yes | no | confirm delete backup |
| `CloudDocPickerDialog` | `mindnavigator/workspaces/objects_workspace.py:398` (`ObjectsWorkspace._import_description`) | `dialog.exec()` at `mindnavigator/workspaces/objects_workspace.py:400` | yes | no | pick source document |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:933` (`ObjectsWorkspace._add_object`) | `dialog.exec()` at `mindnavigator/workspaces/objects_workspace.py:935` | yes | no | add object card |
| `ObjectEditDialog` | `mindnavigator/workspaces/objects_workspace.py:946` (`ObjectsWorkspace._edit_current_object`) | `dialog.exec()` at `mindnavigator/workspaces/objects_workspace.py:954` | yes | no | edit object card |
| `CloudImagePickerDialog` | `mindnavigator/workspaces/objects_workspace.py:988` (`ObjectsWorkspace._attach_images`) | `dialog.exec()` at `mindnavigator/workspaces/objects_workspace.py:992` | yes | no | attach cloud images |
| `QDialog` (ad-hoc image preview) | `mindnavigator/workspaces/objects_workspace.py:1084` (`ObjectsWorkspace._preview_image`) | `dialog.exec()` at `mindnavigator/workspaces/objects_workspace.py:1104` | yes | no | simple image preview |
| `ImagePreviewDialog` | `mindnavigator/workspaces/files_workspace.py:846` (`FilesWorkspace._open_image_preview`) | `showFullScreen()` + `dialog.exec()` at `mindnavigator/workspaces/files_workspace.py:868` and `mindnavigator/workspaces/files_workspace.py:869` | yes | fullscreen | dedicated file image viewer |
| `MapImagePreviewDialog` | `mindnavigator/workspaces/maps_workspace.py:888` (`MapCanvas._open_image_attachment`) | `dialog.exec()` at `mindnavigator/workspaces/maps_workspace.py:908` | yes | no | map-linked image preview |
| `QDialog` (`MapAttachmentDialog`) | `mindnavigator/workspaces/maps_workspace.py:910` (`MapCanvas._open_attachment_view`) | `dialog.exec()` at `mindnavigator/workspaces/maps_workspace.py:1023` | yes | no | linked entity metadata |
| `MapLabelEditDialog` | `mindnavigator/workspaces/maps_workspace.py:1812` (`MapCanvas._edit_selected_marker`) | `dialog.exec()` at `mindnavigator/workspaces/maps_workspace.py:1836` | yes | conditional resize-request handling | marker edit dialog |
| `QDialog` (`MapLabelViewDialog`) | `mindnavigator/workspaces/maps_workspace.py:1862` (`MapCanvas._view_marker`) | `dialog.exec()` at `mindnavigator/workspaces/maps_workspace.py:2214` | yes | yes: `resize(980, 680)`, `setMinimumSize(760, 520)` | marker read-only/details view |
| `MapEditDialog` | `mindnavigator/workspaces/maps_workspace.py:3554` (`MapsListWorkspace._on_edit_map`) | `dialog.exec()` at `mindnavigator/workspaces/maps_workspace.py:3568` | yes | no | edit map card |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1378` (`MapLabelEditDialog._choose_image`) | `dialog.exec()` at `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1381` | yes | no | choose marker image |
| `EntityPickerDialog` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1480` (`MapLabelEditDialog._open_picker`) | `dialog.exec()` at `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1509` | yes | yes: picker repositions to anchor in `showEvent` via `move(anchor_pos)` (`mindnavigator/ui/dialogs/entity_picker_dialog.py:144`) | frameless popup chooser |
| `AttachFileSelectNav` | `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1518` (`MapLabelEditDialog._open_file_picker`) | `dialog.exec()` at `mindnavigator/ui/dialogs/map_label_edit_dialog.py:1521` | yes | no | add file link to marker |

## 4) Special cases

- Already frameless/custom-titlebar-like dialogs:
  - `EntityPickerDialog` uses `Qt.Popup | Qt.FramelessWindowHint` (`mindnavigator/ui/dialogs/entity_picker_dialog.py:51`) and anchor-based popup positioning (`mindnavigator/ui/dialogs/entity_picker_dialog.py:144`).
- Overlay/backdrop implementation already present:
  - `exec_with_overlay(...)` + `ModalOverlay` in `mindnavigator/ui/modals.py:47` and `mindnavigator/ui/modals.py:18`.
  - Overlay geometry is synced with parent via `ModalOverlay._sync_geometry()` (`mindnavigator/ui/modals.py:32`).
- Dialogs with unique size/fullscreen behavior:
  - `TaskImagePreviewDialog` fullscreen (`mindnavigator/workspaces/tasks_workspace.py:839`).
  - `MapImagePreviewDialog` fullscreen (`mindnavigator/workspaces/maps_workspace.py:682`).
  - `ImagePreviewDialog` opened with `showFullScreen()` before exec (`mindnavigator/workspaces/files_workspace.py:868`).
  - `MapLabelViewDialog` fixed baseline size policy via `resize(980, 680)` + `setMinimumSize(760, 520)` (`mindnavigator/workspaces/maps_workspace.py:1867`).
  - `MapLabelEditDialog` runtime screen-fit logic (`setMaximumSize`, center/move) in `_fit_to_screen()` (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:1135`).
- Dialogs that appear non-modal/popup-like by design:
  - `EntityPickerDialog` (`Qt.Popup`) is the main non-modal-style/overlay-less selection surface.

