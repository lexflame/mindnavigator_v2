# DIALOG Map

Purpose: dialog registry and invocation map.

## Registry
- `AttachFileSelectNav` (`mindnavigator/ui/dialogs/attach_file_select_nav.py:39`)
- `MNBaseDialog` (`mindnavigator/ui/dialogs/base_dialog.py:8`)
- `CollectionCategorySelectDialog` (`mindnavigator/ui/dialogs/collection_category_dialog.py:24`)
- `CollectionImportDialog` (`mindnavigator/ui/dialogs/collection_import_dialog.py:19`)
- `EntityPickerDialog` (`mindnavigator/ui/dialogs/entity_picker_dialog.py:38`)
- `MapLabelEditDialog` (`mindnavigator/ui/dialogs/map_label_edit_dialog.py:573`)
- `PurchaseAddByUrlDialog` (`mindnavigator/ui/dialogs/purchase_add_dialog.py:45`)
- `PurchaseCompareDialog` (`mindnavigator/ui/dialogs/purchase_compare_dialog.py:23`)
- `PurchaseEditDialog` (`mindnavigator/ui/dialogs/purchase_edit_dialog.py:21`)
- `ConfirmDialog` (`mindnavigator/ui/modals.py:59`)
- `CollectionMediaPreviewDialog` (`mindnavigator/workspaces/collections_workspace.py:159`)
- `CollectionItemEditDialog` (`mindnavigator/workspaces/collections_workspace.py:340`)
- `CollectionRelationDialog` (`mindnavigator/workspaces/collections_workspace.py:465`)
- `ImagePreviewDialog` (`mindnavigator/workspaces/files_workspace.py:171`)
- `MapEditDialog` (`mindnavigator/workspaces/maps_workspace.py:455`)
- `MapImagePreviewDialog` (`mindnavigator/workspaces/maps_workspace.py:690`)
- `OverlayEditDialog` (`mindnavigator/workspaces/maps_workspace.py:812`)
- `ObjectEditDialog` (`mindnavigator/workspaces/objects_workspace.py:318`)
- `CloudDocPickerDialog` (`mindnavigator/workspaces/objects_workspace.py:414`)
- `CloudImagePickerDialog` (`mindnavigator/workspaces/objects_workspace.py:484`)
- `ProjectEditDialog` (`mindnavigator/workspaces/projects_workspace.py:1055`)
- `ProjectAreaEditDialog` (`mindnavigator/workspaces/projects_workspace.py:1253`)
- `QuickProjectCreateDialog` (`mindnavigator/workspaces/tasks_workspace.py:127`)
- `TaskImagePreviewDialog` (`mindnavigator/workspaces/tasks_workspace.py:1018`)
- `TaskDetailsDialog` (`mindnavigator/workspaces/tasks_workspace.py:1125`)
- `TaskEditDialog` (`mindnavigator/workspaces/tasks_workspace.py:1548`)
- `TaskCreateDialog` (`mindnavigator/workspaces/tasks_workspace.py:2316`)

## Dialog Infrastructure
- Modal helpers: `mindnavigator/ui/modals.py` (`exec_with_overlay`, `show_dialog_standard`, `ConfirmDialog`).
- Frameless patch: `mindnavigator/ui/dialogs/frameless_patch.py` (`dialog_category` behavior).

## Critical Dialog Families
- Tasks: `TaskCreateDialog`, `TaskEditDialog`, `TaskDetailsDialog`, `QuickProjectCreateDialog`.
- Projects: `ProjectEditDialog`, `ProjectAreaEditDialog`.
- Maps: `MapEditDialog`, `MapLabelEditDialog`, `OverlayEditDialog`.
- Collections/Purchases/Files/Objects: dedicated dialogs under `mindnavigator/ui/dialogs/` and workspace modules.
