# Task Plan: TASK_8D2A4F9B-1B37-4A9B-9B8E-5A3D2E1C7F40

## Title
Requirements and UX flow for nested projects and project Drag&Drop.

## Objective
Define strict interaction rules and acceptance criteria for project hierarchy and Drag&Drop before implementation.

## Baseline Findings
1. `ProjectsNav` currently renders flat project entries and has no tree/DnD behavior.
2. Storage already has `projects.parent_project_id` and index `idx_projects_parent`.
3. Storage update flow already prevents direct cycles via ancestry checks in `update_project`.

## Decomposition
1. Hierarchy constraints
- Max hierarchy depth for MVP: 4 levels.
- Root projects allowed (`parent_project_id = NULL`).
- Archive behavior: archived parent hides children by default in active view.
- Self-parent and cyclical ancestry are forbidden.

2. Drag&Drop behavior matrix
- Drop `on item` -> reparent as child (if valid).
- Drop `above/below item` -> reorder among siblings under the same parent.
- Drop on empty root area -> move to root.
- Drop on own descendant -> reject.
- Drop that exceeds max depth -> reject.

3. Visual UX rules
- Show drop indicator line for reorder and node highlight for reparent.
- Show invalid-drop state (red indicator/no-op cursor).
- Preserve expand/collapse state during drag session.
- Keep selection on moved item after successful drop.

4. Data consistency rules
- Persist parent and order atomically in one transaction.
- Recompute sibling order after move.
- Reload should restore exact structure and ordering.

5. MVP architecture split
- Model/storage: tree relations, order persistence, cycle/depth checks.
- Presenter/controller: drag intent resolution and validation.
- View (`ProjectsNav`): tree rendering, indicators, and interaction events.

## Deliverables
- Interaction spec for nested project operations.
- DnD behavior matrix with accepted/rejected scenarios.
- Acceptance criteria for manual QA and automated tests.

## Acceptance Criteria
- All valid/invalid drop paths are explicitly defined.
- Cycle/depth constraints are deterministic and testable.
- Post-drop selection and expansion behavior are consistent.
- Persisted hierarchy and order survive app restart.
