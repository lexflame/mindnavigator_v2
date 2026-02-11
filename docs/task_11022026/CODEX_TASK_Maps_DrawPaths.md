# CODEX TASK: Maps: Draw Transportation Paths

## Goal
Implement drawing and editing of transportation paths (roads/rails/etc.) on the map, with persistence and rendering.

## Definition of Done
- User can draw and edit polyline paths.
- Paths persist and render with correct z-order.

---

## Step 1: Add polyline/path drawing tool
**Modify:** map editor workspace

Implement tool mode: `DrawPath`
- Click to add points, double-click to finish.
- Snap points to grid optionally (toggle).
- Support editing: select path, move points, delete point.

**Acceptance check:**
- User can create a path polyline and finish it.
- Path points are stored in map coordinates.


---

## Step 2: Persist and render paths
**Modify:** map model storage

Store paths in map data `map.paths[]`:
- `{id, name, points:[{x,y}], type:"road|rail|river", style:{stroke,width}}`

Render on overlay layer above tiles but below markers (choose consistent z-order).

**Acceptance check:**
- Paths render correctly and persist.
- Z-order does not hide markers unexpectedly.
