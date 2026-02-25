# AGENTS.md (Repo Template)

## Mission
Deliver minimal, correct, reversible changes for `mindnavigator_v2`.

## Rule Priority
- Direct task request.
- Repository `AGENTS.md` in project root.
- `.codex/rules/*`.

## Working Rules
- Search first with `rg`.
- Inspect call sites before edits.
- Prefer in-place changes over broad refactors.
- Keep patches task-scoped and avoid unrelated rewrites.
- Keep Windows-only logic guarded by `sys.platform == "win32"`.
- Use timezone-aware UTC (`datetime.now(timezone.utc)`).

## Execution Modes

### Default Mode (Always)
- Implement minimal patch.
- Preserve stable desktop behavior unless task explicitly requires behavior changes.
- Run validation for changed scope.

### Sprint/Release Mode (Explicitly Requested)
- Use dedicated sprint branch.
- Track `TASK_GUID` and update `.codex/HISTORY_TASK.md`.
- Log meaningful actions in `.codex/HISTORY_ACTION.md`.
- Use commit prefixes:
  - feature: `feat//:: TASK_GUID`
  - fix: `fix//:: TASK_GUID`
  - parity: `parity::// TASK_GUID`
- Push only after successful validation and when requested/required.

## Git Rules
- One task maps to one commit when commits are requested.
- Do not create intentional broken-state commits unless explicitly requested.

## Required Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests -k <scope>`
- If tests are not run, state why.

## Output Contract
- Changed files.
- Validation commands and results.
- Known residual risks and follow-up options.
