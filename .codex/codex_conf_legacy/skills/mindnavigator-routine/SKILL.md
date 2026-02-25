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
   - `python -m compileall mindnavigator main.py`
   - `pytest tests -k <scope>`
5. Return concise change + validation report.

## Constraints
- No unrelated edits.
- No destructive file operations unless explicitly requested.
- Preserve desktop UX behavior.
