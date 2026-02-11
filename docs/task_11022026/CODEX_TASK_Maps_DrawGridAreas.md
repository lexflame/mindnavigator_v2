# CODEX TASK: Maps: Draw Grid-based Areas

## Goal
Implement drawing of rectangular areas on the map snapped to a coordinate grid, with persistence and rendering.

## Definition of Done
- User can draw areas snapped to grid.
- Areas render as overlays.
- Areas persist with the map data.

---

## Step 1: Add grid-snapped rectangle drawing tool
**Modify:** map editor workspace (e.g., `mindnavigator/ui/workspaces/maps_workspace.py` or `editor_map_workspace.py`)

Implement tool mode: `DrawArea`
- Mouse drag creates rectangle.
- Rectangle corners snap to grid coordinates (grid size already exists or define `grid_step`).
- Store area as list of grid points or as rect in map coordinates.

**Acceptance check:**
- User can drag to create a snapped rectangle.
- Coordinates align to grid increments.


---

## Step 2: Persist areas and render them
**Modify:** map model storage

Store areas in map data (e.g., `map.areas[]`):
- `{id, name, rect:{x,y,w,h}, style:{stroke,fill,opacity}}`

Render areas on map overlay layer.

**Acceptance check:**
- Areas are visible after creation and after reload (if persistence exists).
