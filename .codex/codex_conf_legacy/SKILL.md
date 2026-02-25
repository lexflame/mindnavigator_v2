# SKILL.md (Routine Execution)

## When to Use
Use for routine work: bugfixes, small features, refactors, test updates, release prep.

## Fast Task Flow
1. Read request and locate target modules with `rg`.
2. Inspect related usages and public call paths.
3. Implement smallest safe change.
4. Run focused validation:
   - `python -m compileall mindnavigator main.py`
   - `pytest tests -k <scope>`
5. If needed, run broader suite:
   - `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_run_tmp`
6. Summarize:
   - what changed
   - why
   - what was validated
   - known risks / follow-ups

## Quality Rules
- Keep naming/style aligned with touched files.
- Add comments only for non-obvious logic.
- Avoid new dependencies unless necessary.
- Do not refactor unrelated modules in the same task.

## Debug Sprint Notes
- Marker features (`marker_color`, `marker_theme`): implement end-to-end in storage, model, dialog, delegate.
- Width-sensitive list rendering changes: localize in delegate/constants first.
- If pytest tmpdir ACL fails in this environment, use focused tests with `PYTHONPATH=.`.
