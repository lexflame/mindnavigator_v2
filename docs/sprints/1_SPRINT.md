# Sprint 1: Smooth Drag&Drop Class (Python)

## Sprint Goal
Create a reusable Python class for visually polished and smooth Drag&Drop with clear API, stable behavior, and test coverage.

## Scope
- Primary target: desktop UI module in `mindnavigator/`
- Pattern: MVP (Presenter-driven behavior, View-only rendering)
- Out of scope: full redesign of existing UI screens

## Task List
1. `TASK_GUID: TASK_8A7C1F61-0F8F-4E7A-9E75-DC0C0EBE9F11` - Product and UX requirements
- Define Drag&Drop interaction rules (start threshold, hover behavior, drop acceptance, cancel behavior).
- Define performance targets (fps, max jank, expected latency).
- Define keyboard/mouse fallback behavior.

2. `TASK_GUID: TASK_6F4219EE-B4D0-4B2A-93F8-0A8E1F17CC90` - Architecture and design (MVP)
- Design `DragDropController` responsibilities in Presenter layer.
- Define interface contracts for View events and callbacks.
- Define extension points for custom payload and validators.

3. `TASK_GUID: TASK_2C33A47A-50D5-4A1A-8CFD-74FC0A3F4A62` - Core data model
- Create payload model for dragged item metadata.
- Create drag session state model (idle, arming, dragging, dropping, canceled).
- Add serialization/trace-friendly debug fields.

4. `TASK_GUID: TASK_4DE11127-2AFA-42C4-B3D0-D83E4F89B8C4` - Class skeleton and API
- Implement base class with public API:
  - `begin_drag(...)`
  - `update_drag(...)`
  - `end_drag(...)`
  - `cancel_drag(...)`
- Add event hooks for `on_drag_start`, `on_drag_move`, `on_drop`, `on_cancel`.

5. `TASK_GUID: TASK_C4D406F4-3D37-43D8-A3BE-4D6B655B4A8A` - Smooth motion engine
- Add interpolation/easing for drag ghost movement.
- Implement frame-synced position updates.
- Add configurable motion profile (linear, ease-out, spring-like).

6. `TASK_GUID: TASK_B91FE4A6-8FA1-4978-A4FB-7E6F65A0E650` - Visual polish layer
- Add drag ghost preview with opacity and scale effects.
- Add hover highlight for valid/invalid drop zones.
- Add subtle transition animation on drop success/failure.

7. `TASK_GUID: TASK_9D03E4C5-5A3D-4416-8A37-1D5CE2E0D61B` - Hit testing and drop validation
- Implement robust hit-test strategy for nested widgets.
- Add zone-level validation rules.
- Add clear rejection feedback path.

8. `TASK_GUID: TASK_83D9C1A2-88C9-45FA-9473-1EBECF58B2DA` - Input and interaction edge cases
- Handle fast cursor moves and leaving window bounds.
- Handle canceled drags (Esc / mouse release outside zone).
- Handle multi-monitor DPI/scaling offsets.

9. `TASK_GUID: TASK_43F6DE9B-40D4-42CE-91E6-B65B1F42D96A` - Performance and stability
- Add lightweight profiling around drag loop.
- Reduce allocations in high-frequency move updates.
- Ensure no UI thread blocking in drag path.

10. `TASK_GUID: TASK_D86A66D1-6A6D-44BB-87B5-73ED2371D4D5` - Automated tests
- Unit tests for state transitions and validator rules.
- Integration tests for drag lifecycle across multiple drop zones.
- Regression tests for canceled drag and invalid drop.

11. `TASK_GUID: TASK_E5AB0A74-9E13-4FC3-902D-8A2FA3DE3D10` - Demo and developer docs
- Add minimal demo screen that showcases class behavior.
- Document integration steps and API usage examples.
- Document tuning parameters for smoothness/latency tradeoff.

12. `TASK_GUID: TASK_0F1733D2-3B9F-4E8D-BD6A-0C2F5F55189E` - Build and release readiness
- Verify build scripts include new module paths if required.
- Run full pre-commit validation for changed areas.
- Prepare final sprint summary and risk list.

## Definition of Done
- Drag&Drop class is reusable and integrated into at least one screen.
- Behavior is smooth and visually consistent under normal load.
- Stable automated tests are present and passing.
- Public API and usage documentation are complete.
