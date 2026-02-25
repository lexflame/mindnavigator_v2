# CHECKLIST.md

## Before Finishing
- [ ] Only task-related files were changed.
- [ ] No accidental behavioral changes in desktop flow.
- [ ] `python -m compileall mindnavigator main.py` passed.
- [ ] Focused tests for changed scope passed (or limitation documented).
- [ ] Windows-specific logic remains guarded by `sys.platform == "win32"`.
- [ ] Storage changes include migration + read/write path updates.
- [ ] Final summary includes changed files, validations, and residual risks.
