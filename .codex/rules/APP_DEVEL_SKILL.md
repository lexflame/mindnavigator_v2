# APP_DEVEL_SKILL.md

## Purpose
Operational workflow for tasks in this repository under `APP_DEVEL_AGENTS.md` policy.

## Rule Allocation
- This file defines execution flow and command triggers.
- Policy constraints remain in `APP_DEVEL_AGENTS.md`.

## Default Task Flow
1. Analyze task and locate target modules.
2. Review impacted call sites before edits.
3. Implement minimal in-place patch aligned with MVP boundaries.
4. Run validation for changed scope:
   - `python -m compileall mindnavigator main.py` (for code changes)
   - `pytest tests -k <changed_scope>`
5. Report:
   - changed files
   - validation results
   - residual risks

## Sprint/Release Extensions
Apply this section only when the task is explicitly sprint/release work.
1. Assign and record `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md` with status.
3. Append meaningful actions to `.codex/HISTORY_ACTION.md`.
4. Work in dedicated sprint branch.
5. If commits are requested, use prefixes:
   - feature: `feat//:: TASK_GUID`
   - fix: `fix//:: TASK_GUID`
   - parity: `parity::// TASK_GUID`
6. Push only when requested/required and after successful validation.

## Build Script Maintenance Flow (Release Scope)
- Keep scripts updated when build/release is part of the task:
  - `scripts/build_win.bat`
  - `scripts/build_start_win.bat`
  - `scripts/build_win.sh`
  - `scripts/build_start_win.sh`

## Packaging Validation Checklist (Release Scope)
- Verify compiled app directories:
  `lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `definition`.
- Verify compiled app root is minimal and includes DB cleanup script.
- For deployment target `C:\Program Portable\MindNavigator\`, use `assets/icon.ico`.

## CODEX CLI Triggers
- `b_start`: build + compile + place into `C:\Program Portable\MindNavigator\` + run.
- `b_build`: build + compile + place into `C:\Program Portable\MindNavigator\` + do not run.

## Notes
- Use git keys from `.codex/git_key/` when authenticated git operations are required.
