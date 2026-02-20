# APP_DEVEL_SKILL.md

## Purpose
Operational workflow skill for executing tasks in this repository under `APP_DEVEL_AGENTS.md` policy.

## Rule Allocation
This SKILL file owns execution flow and command triggers.
Policy constraints remain in `APP_DEVEL_AGENTS.md`.

## Standard Task Flow
1. Assign and record a new `TASK_GUID`.
2. Decompose the task before coding:
   - analysis
   - solution design
   - planned refactor of impacted existing code
3. Update `.codex/HISTORY_TASK.md` with task metadata and current status.
4. Append every meaningful command/action and result summary to `.codex/HISTORY_ACTION.md` in chronological shell-history format.
5. Implement changes following MVP boundaries.
6. Ensure/extend stable automated tests for changed behavior.
7. Run tests before commit.
8. Commit using required prefix with `TASK_GUID`.
9. If a fix is needed during execution:
   - commit pre-fix state
   - commit fix state with `fix//:: TASK_GUID`
10. Push after successful tests.

## Commit Prefix Quick Rules
- Feature work: `feat//:: TASK_GUID`
- Fix work: `fix//:: TASK_GUID`
- Parity work: `parity::// TASK_GUID`

## Sprint Execution
- Work only inside a dedicated sprint branch.

## Build Script Maintenance Flow
- Keep build scripts updated and runnable:
  - `scripts/build_win.bat`
  - `scripts/build_start_win.bat`
  - `scripts/build_win.sh`
  - `scripts/build_start_win.sh`

## Packaging Validation Checklist
- Verify compiled app contains directories:
  `lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `defenition`.
- Verify compiled app root has minimal files only.
- Verify compiled app root contains DB cleanup script.

## CODEX CLI Triggers
- Phrase `b_start`:
  build + compile + place into `C:\Program Portable\NAME_APP\` + run.
- Phrase `b_build`:
  build + compile + place into `C:\Program Portable\NAME_APP\` + run.

## Notes
- Use git keys from `.codex/git_key/` for git operations.
- Always sync task/action history files during execution.
