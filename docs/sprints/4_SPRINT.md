# Sprint 4: Nested Projects And Project Drag&Drop

## Sprint Goal
Implement hierarchical projects (projects inside projects) and smooth/validated Drag&Drop for project reordering and reparenting.

## Scope
- Primary target: project domain model, storage layer, projects navigation UI, and drag/drop interaction handling.
- Include migration and compatibility for existing flat project data.
- Out of scope: cross-workspace visual redesign unrelated to project hierarchy.

## Task List
1. `TASK_GUID: TASK_8D2A4F9B-1B37-4A9B-9B8E-5A3D2E1C7F40` - Requirements and UX flow for nested projects
- Define allowed hierarchy depth and parent/child constraints.
- Define DnD behavior matrix: reorder sibling, reparent child, invalid drop zones.
- Define acceptance criteria for visual feedback and persistence.

2. `TASK_GUID: TASK_3F1B7D6E-2F8C-4C19-8D6A-B7E21A4D3C91` - Storage model and migration design
- Add parent relation for projects in storage schema.
- Design migration for existing data to keep backward compatibility.
- Define indexes and integrity checks for parent references.

3. `TASK_GUID: TASK_5A9E2C71-6D44-4B69-B193-0E4A3C1F2D88` - Domain API for project tree operations
- Implement create/move/reparent APIs with validation.
- Prevent cyclic dependencies and invalid self-parenting.
- Add helpers to fetch project tree and flattened ordered views.

4. `TASK_GUID: TASK_2C6D1A9E-7B52-4E8D-8A10-19F2D3B4A5C7` - ProjectsNav UI tree rendering
- Render projects as hierarchical list/tree with indentation.
- Add expand/collapse state handling and persistence.
- Ensure selection/filter behavior remains stable with nesting.

5. `TASK_GUID: TASK_7E3A9B4D-0C11-4F8E-9D2F-6A1B8C3E5D20` - Drag&Drop interaction for projects
- Enable drag source and drop targets for project items.
- Support sibling reorder and parent reassignment.
- Add drop indicator visuals and hover feedback.

6. `TASK_GUID: TASK_1B4C8D2E-9F63-4A1B-B2E7-3D6A9C5F7E11` - Validation and guardrails for DnD
- Block drops that create cycles or exceed depth limits.
- Block drops to forbidden pseudo-items/virtual sections.
- Add clear user-facing feedback for rejected drops.

7. `TASK_GUID: TASK_9A2F6D1C-3E47-4B8F-9C11-5D7A2E4B6F33` - Persistence, ordering, and reload consistency
- Persist order and parent changes atomically.
- Ensure state restoration after restart/reload.
- Verify stable ordering between sessions and filters.

8. `TASK_GUID: TASK_4D8B1A6F-2E93-4C7A-A5D1-8F3E6B2C9A44` - Automated tests for tree and DnD logic
- Add unit tests for cycle/depth validation and move operations.
- Add integration tests for UI-level DnD flows.
- Add regression tests for migration and legacy flat projects.

9. `TASK_GUID: TASK_6C1E9A4B-5D72-4F8C-8B3A-2A7D1E9C4F55` - Build and release readiness
- Run compile and targeted test suite for project hierarchy features.
- Update technical docs for project structure and DnD behavior.
- Prepare sprint completion checklist and known limitations.

## Definition of Done
- Projects support nested hierarchy with stable persistence.
- Project Drag&Drop supports reorder/reparent with validation.
- Invalid drops are blocked with clear behavior and no data corruption.
- Tests cover core tree logic, DnD validation, and persistence.
