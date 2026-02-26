---
name: mindnavigator-routine
description: Routine workflow for bug fixes, small features, targeted refactors, and test updates in this repository.
---

# Skill: mindnavigator-routine

## When to Use
Routine repository work: bug fixes, small features, targeted refactors, test updates.

## Inputs
- Task request
- Affected files under `mindnavigator/` and `tests/`

## Procedure
1. Discover scope with `rg`.
2. Read impacted modules and call sites.
3. Implement minimal patch.
4. Validate:
   - `python -m compileall mindnavigator main.py` (for code changes)
   - `pytest tests -k <scope>`
5. Return concise change + validation report with residual risks.

## Sprint/Release Extension (Explicit Tasks Only)
1. Assign `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md` and `.codex/HISTORY_ACTION.md`.
3. Work in dedicated sprint branch.
4. If commits are requested, use prefixes:
   - feature: `feat//:: TASK_GUID`
   - fix: `fix//:: TASK_GUID`
   - parity: `parity::// TASK_GUID`
5. Push only when requested/required and after successful validation.

## Constraints
- No unrelated edits.
- No destructive file operations unless explicitly requested.
- Preserve desktop UX behavior.
