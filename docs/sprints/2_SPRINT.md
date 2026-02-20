# Sprint 2: Scrollbar Styling And Smooth Scroll

## Sprint Goal
Implement a consistent styled scrollbar system and smooth scrolling behavior across key UI workspaces.

## Scope
- Primary target: `mindnavigator/ui/`, `mindnavigator/workspaces/`
- Include both vertical and horizontal scrollbars where relevant.
- Out of scope: redesign of non-scroll UI controls.

## Task List
1. `TASK_GUID: TASK_5B2F6F11-0D53-487E-AF6A-442BFD0C8A61` - UX requirements and baseline audit
- Inventory all scrollable widgets and current behavior.
- Define style tokens (width, radius, hover, active, contrast).
- Define smooth-scroll acceptance criteria (latency, feel, boundaries).

2. `TASK_GUID: TASK_0E28539F-0B13-4E1F-9E80-F9EE8A307039` - Scroll style architecture
- Define centralized style API in `ui/styles.py`.
- Split theme variables from widget-specific scrollbar rules.
- Add reusable helper for applying scrollbar styles.

3. `TASK_GUID: TASK_B5B10AB6-FD2F-4AA1-9157-8E7AA32EA0CD` - Global scrollbar stylesheet
- Implement unified QSS for `QScrollBar` states.
- Add hover/pressed handle states and disabled state handling.
- Ensure style applies to nested scroll areas.

4. `TASK_GUID: TASK_7F4A1A67-1967-4B56-8DAB-1A89F73A9AA4` - Smooth scroll controller
- Add wheel-event smoothing/interpolation utility.
- Configure per-widget scroll step multipliers.
- Handle trackpad and mouse wheel deltas consistently.

5. `TASK_GUID: TASK_4414D168-37D5-414E-A3F6-0C4A5DA15B0A` - Workspace integration
- Apply new scrollbar style and smooth behavior in key workspaces:
  tasks, notes, files, objects, purchases, collections.
- Add per-workspace exceptions only when strictly necessary.

6. `TASK_GUID: TASK_9B2D3373-C319-4D04-A97B-6F59F165A433` - Edge-case handling
- Prevent overscroll jitter at min/max boundaries.
- Handle dynamic content size changes during animation.
- Ensure no stuck state when focus changes mid-scroll.

7. `TASK_GUID: TASK_7F2D6F30-0E57-465F-BF6C-EA8F1ED9A148` - Performance and stability
- Profile scroll handler hot paths.
- Cap update frequency to avoid UI thread spikes.
- Ensure smooth behavior with long lists/tables.

8. `TASK_GUID: TASK_A312E8B4-B507-4667-BB2C-B6D0D9CB571E` - Automated tests
- Add unit tests for interpolation and boundary logic.
- Add integration tests for wheel input and viewport updates.
- Add regression tests for fast wheel bursts.

9. `TASK_GUID: TASK_A2DA8B13-D8F5-44D5-88C0-5C95BFB4E1A0` - Demo and docs
- Add a minimal demo for styled + smooth scrolling.
- Document style variables and integration steps.
- Document tuning knobs for speed/smoothness.

10. `TASK_GUID: TASK_10A88701-DA0B-4FA8-85D8-CAECDA1A57E2` - Build and release readiness
- Verify build artifacts include updated style resources.
- Run tests and compile checks.
- Prepare sprint completion notes and risks.

## Definition of Done
- Scrollbars are visually consistent across targeted workspaces.
- Scrolling is smooth and predictable for wheel/trackpad input.
- Automated tests are present and passing.
- Documentation covers setup and tuning.
