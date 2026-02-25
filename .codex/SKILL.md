# Project Skill: mindnavigator-v2

## When to use
Use this skill for routine work in this repository: bugfixes, small features, refactoring, tests, and release prep.

## Quick context
- App entrypoint: `main.py`
- Core code: `mindnavigator/`
- Tests: `tests/`
- Assets/docs: `assets/`, `docs/`

## Standard execution flow
1. Read the task and locate target modules with `rg`.
2. Inspect call sites before changing public behavior.
3. Implement minimal patch in-place.
4. Run targeted validation:
   - `python -m compileall mindnavigator main.py` (for code changes)
   - `pytest tests -k <changed_area>`
5. Report changed files, validation results, and residual risks.

## Sprint/Release extension (explicit tasks only)
1. Assign and record `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md` and `.codex/HISTORY_ACTION.md`.
3. Work in dedicated sprint branch.
4. If commits are requested, use prefixes:
   - feature: `feat//:: TASK_GUID`
   - fix: `fix//:: TASK_GUID`
   - parity: `parity::// TASK_GUID`
5. Push only when requested/required and after successful validation.

## Guardrails
- Keep architecture and naming consistent with nearby code.
- Avoid cross-module rewrites unless explicitly requested.
- Prefer deterministic logic over implicit side effects.

## Done criteria
- Code compiles.
- Relevant tests pass (or explicit note why not run/failing).
- Change summary includes what and why.
