# CHECKLIST.md

## Before Finishing
- [ ] Only task-related files were changed.
- [ ] No accidental behavioral changes in desktop flow.
- [ ] `python -m compileall mindnavigator main.py` passed for code changes.
- [ ] Focused tests for changed scope passed (or limitation documented).
- [ ] Windows-specific logic remains guarded by `sys.platform == "win32"`.
- [ ] Storage changes include migration plus read and write path updates.
- [ ] UI changes include an explicit interaction-path validation note (test or manual check).
- [ ] Build or packaging changes include an explicit build-script and packaging validation note.
- [ ] For sprint, release, parity, or hotfix work: `TASK_GUID` tracking is updated in `.codex/HISTORY_TASK.md`.
- [ ] For sprint, release, parity, or hotfix work: meaningful actions are appended to `.codex/HISTORY_ACTION.md`.
- [ ] For sprint work: branch, commit, push, and pipeline status are aligned with the current delivery step.
- [ ] Final summary includes changed files, validations, residual risks, and the next practical step.
