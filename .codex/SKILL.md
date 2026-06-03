# Project Skill: mindnavigator-v2

## Purpose
Primary execution workflow for routine repository work in `mindnavigator_v2`.
Use this file together with `.codex/AGENTS.md`; if there is a conflict, `.codex/AGENTS.md`
takes precedence.

This skill is based on the current project workflow plus lessons from the recent task branches:
- `feat/remastering_edit_window_project`
- `feat/remaster-task-window`
- `codex/fix-task-menu-edit-minimize`
- `feature/projects-custom-properties-and-task-integration`

## Rule Priority
1. Direct task request.
2. `.codex/AGENTS.md`.
3. This file: `.codex/SKILL.md`.
4. Supporting reference files inside `.codex/`.

## Scope
- Work only inside this repository root.
- Use this skill for bug fixes, small features, targeted refactors, UI remastering, tests, and release preparation.
- Keep patches minimal, task-scoped, and reversible.
- Preserve stable desktop behavior unless the task explicitly requires behavior changes.
- Preserve public interfaces, storage formats, and settings unless the task explicitly requires a breaking change.

## Quick Context
- App entrypoint: `main.py`
- Core code: `mindnavigator/`
- Tests: `tests/`
- Assets and docs: `assets/`, `docs/`
- Desktop UI: PySide6 / Qt Widgets
- Storage: SQLite facade in `mindnavigator/storage/`

## Default Task Flow
1. Inspect Git state with `git status --short --branch` and `git branch --show-current`.
2. If the current branch is protected or unrelated to the task, create a dedicated task branch before editing.
3. If uncommitted or untracked user changes exist, identify whether they are task inputs or unrelated user work; do not overwrite them.
4. Read task materials first: markdown specs, screenshots, prototypes, existing tests, and related code.
5. Locate target modules with `rg`; inspect call sites before changing public behavior.
6. Define the smallest deliverable slice that can be validated.
7. Implement in-place using existing architecture and local helpers.
8. Run validation for the changed scope.
9. Commit task-scoped changes when the implementation is complete.
10. Report changed files, validation results, residual risks, and the next practical step.

## Recent Branch Lessons
### UI Remastering
- Preserve the existing data and save contract first; remaster layout around it.
- Prefer staged UI changes: header, body columns, right panel, footer, then interaction fixes.
- Reuse existing editors, validators, selectors, and storage calls before adding abstractions.
- Use application theme tokens (`ThemePalette`, shared styles) instead of local one-off color schemes.
- Treat prototypes and screenshots as input artifacts; do not commit them unless explicitly requested.
- When preview and edit modes share a dialog, keep real editors as the source of truth and layer read-only display widgets over them.
- Keep scroll behavior intentional: headers and footers stay accessible, body content scrolls, horizontal scrollbars stay off unless explicitly required.

### Qt Interaction Reliability
- For painted list actions, centralize hit-zone geometry and reuse it in `paint`, event handling, and tests.
- If a delegate event is unreliable for a user action, handle the event in the owning view (`QListView`, `QTreeView`, etc.) where the real mouse position is guaranteed.
- Avoid protected cross-class calls for new interactions; expose public methods such as `open_project_editor()` when another widget must trigger behavior.
- Test interaction paths with the same widget layer that receives the real event, not only the helper method.
- Modal dialogs opened from context menus should be deferred or opened after the menu closes to avoid activation/minimize regressions.

### Storage And Cross-Module Features
- For custom project/task properties, implement end-to-end:
  - schema and migration
  - dataclasses
  - fetch/create/update SQL
  - model roles
  - edit dialogs
  - delegate rendering
  - CSV/import-export path when relevant
  - focused tests
- When a UI remaster moves fields, re-check propagation behavior for nested tasks and child entities.
- Do not silently drop existing group actions, property propagation, or attachment flows during layout work.

### Tests And Validation
- Always run `python -m compileall mindnavigator main.py` for code changes.
- Run focused tests for the changed surface:
  - project UI/storage: `python -m pytest tests -k project -q`
  - task details/editing: `python -m pytest tests -k "task or dialog" -q`
  - context linking: `python -m pytest tests/test_context_entity_linking.py -q`
- Add or update tests for bug fixes, especially when the bug is an event routing, modal, layout, or propagation regression.
- If only documentation or skill files changed, no Python validation is required; inspect the diff and state that code tests were skipped because no code changed.

## Collaboration Gate
Use a lightweight collaboration check for broad or cross-module work. This is not required for tiny local fixes.

Run the gate before implementation when any of these are true:
- the change crosses UI, storage, and model boundaries;
- the change affects persistence, migrations, CSV, or public settings;
- the change changes a repeated workflow users rely on;
- prototypes/specs imply multiple stakeholders or unclear acceptance criteria.

For the gate, identify:
- **Accountable**: the single decision owner, usually the requesting user.
- **Responsible**: Codex implementing the change.
- **Consulted inputs**: task spec, screenshots/prototypes, existing tests, existing code, prior branch lessons.
- **Affected surfaces**: UI modules, storage modules, models, tests, packaging if relevant.
- **Surprise risks**: behaviors that could change unexpectedly, such as propagation, modal activation, scroll behavior, or saved settings.

If the gate exposes missing input that would materially change implementation, ask one concise question. Otherwise proceed and document assumptions.

## UI Implementation Rules
- Keep UI rendering and event handling in UI/workspace/delegate modules.
- Keep storage and SQL logic in `mindnavigator/storage/`.
- Match existing design system and application palette.
- Prefer stable geometry constraints for toolbars, cards, hit zones, and fixed-format UI elements.
- Avoid nested cards; use cards for sections, repeated items, and framed tools.
- Use Qt6 enum namespaces (`Qt.AlignmentFlag.*`, `QEvent.Type.*`, etc.).
- For `QDialogButtonBox`, create the box and add buttons via `addButton`.
- Keep labels and compact controls readable at the minimum supported window size.

## Git And Change Hygiene
- Keep one focused branch per task.
- Keep commits task-focused; do not mix prototype data, code changes, and unrelated docs unless requested.
- Never revert user changes unless explicitly requested.
- If untracked task materials are present, leave them untracked unless the user asks to add them.
- Use non-interactive git commands.
- Do not push, merge, rebase, or create PRs without explicit user request and successful validation.

## Validation Gates
### Minimum Before Final Response
- Code changes: `python -m compileall mindnavigator main.py`
- Behavior changes: focused pytest for the changed scope.
- Documentation-only changes: inspect `git diff --stat` and `git diff -- .codex/SKILL.md`; state that code tests were not needed.

### Conditional Gates
- Storage schema changes: validate migration plus read and write paths together.
- UI behavior changes: validate the affected interaction path with a test or explicit manual verification note.
- Build or packaging changes: validate touched build scripts and packaging assumptions.

### Reporting Contract
- Report exact validation commands.
- Report meaningful outcomes.
- Report residual risks explicitly.

## Command Map
### Navigation
- Find files: `rg --files`
- Find symbol or text: `rg -n "<pattern>" mindnavigator tests .codex`

### Validation
- Syntax check: `python -m compileall mindnavigator main.py`
- Focused tests: `python -m pytest tests -k <scope> -q`
- Full tests, env-safe: `python -m pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

### Git Hygiene
- Status: `git status --short --branch`
- Current branch: `git branch --show-current`
- Diff summary: `git diff --stat`
- Changed files: `git diff --name-only`

## Sprint And Release Mode
Apply only when the task is explicitly sprint, release, parity, or hotfix work.
1. Assign and record a `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md` for task creation and status transitions.
3. Append meaningful chronological entries to `.codex/HISTORY_ACTION.md`.
4. Work in a dedicated sprint branch.
5. Use one task-focused commit when commits are requested.
6. If commits are requested, use prefixes:
- feature: `feat//:: TASK_GUID`
- fix: `fix//:: TASK_GUID`
- parity: `parity::// TASK_GUID`
7. Push only after successful validation and only when push is requested or required by the sprint flow.

## Build And Packaging Rules
Apply when build, packaging, or release delivery is in scope.
- Keep these scripts aligned with delivered behavior:
- `scripts/build_win.bat`
- `scripts/build_start_win.bat`
- `scripts/build_win.sh`
- `scripts/build_start_win.sh`
- Preserve packaged directories:
- `lib`
- `assets`
- `conf`
- `data`
- `local_data`
- `lang`
- `defenition`
- For deployment target `C:\Program Portable\MindNavigator\`, use `assets/icon.ico`.

## Finish Checklist
- Task materials were read before implementation.
- Only task-related files were changed.
- Existing behavior and public contracts were preserved unless explicitly changed.
- UI changes use application theme tokens and tested interaction paths.
- Storage changes include migration plus read/write validation.
- `python -m compileall mindnavigator main.py` passed for code changes.
- Focused tests passed, or the limitation is documented.
- Final summary includes changed files, validation results, residual risks, and final status.

## Supporting References
- `.codex/AGENTS.md` is authoritative project policy.
- `.codex/CHECKLIST.md` and `.codex/COMMANDS.md` remain quick-reference companions.
- `.codex/rules/*.md` remain modular rule sources for audit and reuse.
- `.codex/skills/mindnavigator-routine/SKILL.md` should stay aligned with this file because it is the enabled project skill in `.codex/config.toml`.
- `.codex/COLLABORATION_SKILL.md` is a template source for full RACI/collaboration audits when a lightweight gate is not enough.
