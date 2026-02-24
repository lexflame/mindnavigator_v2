# PROPERTY Map

Purpose: entity property map and UI role map.

## Storage Dataclasses
- Source file: `mindnavigator/storage.py`.
- Main entities: `TaskData`, `ProjectData`, `MapData`, `MapMarkerData`, `NoteData`, `ObjectData`, `CollectionItemData`, `Shop*Data`, `Wishlist*Data`.
- Task properties include hierarchy and planning fields (`parent_id`, recurrence, gantt).
- Project properties include hierarchy and linkage fields (`parent_project_id`, linked map/note/object, `sort_order`).

## Settings Keys (current)
- `cloud_storage_path`
- `backup_dir`
- `backup_include_cloud`
- `backup_auto_enabled`
- `backup_frequency`
- `backup_retention`
- `backup_last_run`

## UI Role Sets
- `TaskRoles`: task/day/header rendering roles in tasks list.
- `ProjectRoles`: project/header/tree rendering roles in projects list.
- `MapRoles`, `ObjectRoles`, `NoteRoles`: workspace-specific role sets.
