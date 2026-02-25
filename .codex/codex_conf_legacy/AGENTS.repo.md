# AGENTS.md (Repo Template)

## Mission
Deliver minimal, correct, reversible changes for `mindnavigator_v2`.

## Working Rules
- Search first with `rg`.
- Inspect call sites before edits.
- Prefer in-place changes over broad refactors.
- Keep Windows-only logic guarded by `sys.platform == "win32"`.
- Use timezone-aware UTC (`datetime.now(timezone.utc)`).

## Required Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests -k <scope>`

## Output Contract
- Changed files.
- Validation result.
- Known risks and follow-up options.
