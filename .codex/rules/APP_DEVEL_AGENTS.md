# APP_DEVEL_AGENTS.md

## Purpose
Repository-level policy for Codex agents.
This file defines policy constraints. Execution flow is defined in `APP_DEVEL_SKILL.md`.

## Rule Allocation
- Policy rules live in this file.
- Operational steps and command triggers live in `APP_DEVEL_SKILL.md`.

## Policy Levels

### Mandatory (Always)
- Keep changes task-scoped and avoid unrelated rewrites.
- Preserve stable desktop behavior unless task explicitly requires behavior changes.
- Validate changed behavior before final response.
- Keep architecture consistent with existing MVP boundaries.

### Sprint/Release Mode (When Task Is Explicitly Sprint/Release)
- Use a dedicated sprint branch.
- Track task identity in `.codex/HISTORY_TASK.md` with a `TASK_GUID`.
- Track meaningful command/action history in `.codex/HISTORY_ACTION.md`.
- Use commit prefixes with task id:
  - feature work: `feat//:: TASK_GUID`
  - fixes: `fix//:: TASK_GUID`
  - parity: `parity::// TASK_GUID`
- Push only after successful validation and when push is requested/required by sprint flow.

## Git Policy
- One task should map to one commit when commits are requested.
- Do not create intentional "broken-state" commits unless explicitly requested for debugging/forensics.
- Use keys from `.codex/git_key/` when repository policy requires authenticated git operations.

## Build And Packaging Policy (Release Tasks)
- Maintain build scripts when build/release pipeline is part of the task:
  - `scripts/build_win.bat`
  - `scripts/build_start_win.bat`
  - `scripts/build_win.sh`
  - `scripts/build_start_win.sh`
- For packaged artifacts, verify required directories:
  `lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `definition`.
- Ensure packaged root includes a DB cleanup script when release packaging is in scope.
