# Task Plan: TASK_8A7C1F61-0F8F-4E7A-9E75-DC0C0EBE9F11

## Title
Product and UX requirements for smooth Drag&Drop.

## Objective
Define concrete interaction and UX requirements for a reusable Drag&Drop class before implementation.

## Decomposition
1. Interaction rules
- Drag start threshold in px and in ms.
- Drag cancel conditions.
- Valid and invalid drop behavior.

2. Visual behavior
- Drag ghost appearance and transparency.
- Hover feedback for valid and invalid targets.
- Drop success and failure transitions.

3. Input behavior
- Mouse-first interaction baseline.
- Keyboard assist rules (cancel, focus, fallback).
- Out-of-window and high-speed cursor behavior.

4. Performance requirements
- Target smoothness: 60 FPS where feasible.
- Max acceptable frame drop/jank window.
- No blocking calls in drag update loop.

5. MVP role split
- View: emits input events, renders ghost/highlights.
- Presenter/controller: state transitions, validation, policies.
- Model: payload and drag session state data.

## Deliverables
- Requirement checklist to implement in `DragDropController`.
- Acceptance criteria list for QA and automated tests.

## Acceptance Criteria
- All interaction states are explicitly defined.
- Valid/invalid drop outcomes are deterministic.
- Performance targets are measurable.
- Requirements are testable with unit or integration tests.
