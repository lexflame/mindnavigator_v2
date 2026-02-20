# Hotfix Notes: TASK_396C7C6F-FEAE-4E6F-86CB-59361FFDF225

## Title
ProjectsNav Drag&Drop fix when project does not move on drop.

## Symptoms
- Drag operation starts, but project is not moved/reordered in list.
- Root drops were difficult because pseudo-items rejected drop target.

## Root Cause
1. Drop source relied mainly on `currentItem()`, which is unstable during drag/drop interaction.
2. Drop intent switched to `as_child` too aggressively by horizontal threshold only.
3. Drop on pseudo-items (`clear/section/empty`) was rejected, preventing practical move-to-root flow.

## Fix
1. Added drag source capture in `startDrag()` (`_drag_source_project_id`).
2. Used captured source id in `dropEvent()` with safe fallback to current item.
3. Allowed root move when dropping on pseudo-items and empty area.
4. Refined intent logic:
- `reorder` near row top/bottom zones,
- `reparent` only in row middle and with stronger horizontal threshold.

## Validation
1. `python -m compileall mindnavigator/ui/projects_nav.py` passed.
