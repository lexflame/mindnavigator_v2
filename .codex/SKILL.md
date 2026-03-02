# Project Skill: mindnavigator-v2

## Purpose
Primary execution workflow for routine repository work in `mindnavigator_v2`.
This file consolidates the practical rules from:
- `.codex/rules/APP_DEVEL_AGENTS.md`
- `.codex/rules/APP_DEVEL_SKILL.md`
- `.codex/rules/10-project-scope.md`
- `.codex/rules/20-validation-gates.md`
- `.codex/CHECKLIST.md`
- `.codex/COMMANDS.md`
- `.codex/skills/mindnavigator-routine/SKILL.md`

## Rule Priority
1. Direct task request.
2. Repository root `AGENTS.md`.
3. This file: `.codex/SKILL.md`.
4. Supporting reference files inside `.codex/`.

## Scope
- Work only inside `D:\_Branch\PROJECTS\project_work\mindnavigator\mindnavigator_v2`.
- Use this skill for routine work: bug fixes, small features, targeted refactors, tests, and release preparation.
- Keep patches minimal, task-scoped, and reversible.
- Preserve stable desktop behavior unless the task explicitly requires behavior changes.
- Preserve backward compatibility unless the task explicitly requires a breaking change.

## Quick Context
- App entrypoint: `main.py`
- Core code: `mindnavigator/`
- Tests: `tests/`
- Assets and docs: `assets/`, `docs/`

## Default Task Flow
1. Analyze the task and locate target modules with `rg`.
2. Review impacted call sites before changing public behavior.
3. Implement the smallest in-place patch that satisfies the task.
4. Run validation for the changed scope.
5. Report changed files, validation results, residual risks, and the next practical step.

## Validation Gates
### Minimum Before Final Response
- Run `python -m compileall mindnavigator main.py` for code changes.
- Run `pytest tests -k <changed_scope>` for changed behavior.
- If tests were not run, state why.

### Conditional Gates
- If storage schema changes, validate migration plus read and write paths together.
- If UI behavior changes, validate the affected interaction path with a test or an explicit manual verification note.
- If build or packaging is in scope, validate the touched build scripts and packaging assumptions.

### Reporting Contract
- Report the exact validation commands you ran.
- Report the meaningful outcomes.
- Report residual risks explicitly.

## Sprint And Release Mode
Apply this section only when the task is explicitly sprint, release, parity, or hotfix work.
1. Assign and record a `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md` for task creation and status transitions.
3. Append meaningful chronological entries to `.codex/HISTORY_ACTION.md`.
4. Work in a dedicated sprint branch.
5. Use one task-focused commit when commits are requested; avoid batching unrelated changes.
6. If commits are requested, use prefixes:
- feature: `feat//:: TASK_GUID`
- fix: `fix//:: TASK_GUID`
- parity: `parity::// TASK_GUID`
7. Push only after successful validation and only when push is requested or required by the sprint flow.

## Git And Change Hygiene
- Keep changes task-scoped and avoid unrelated rewrites.
- Do not create intentional broken-state commits unless explicitly requested.
- Use keys from `.codex/git_key/` when authenticated Git operations are required.
- Prefer deterministic logic over implicit side effects.
- Keep architecture and naming consistent with nearby code.

## Build And Packaging Rules
Apply these when build, packaging, or release delivery is in scope.
- Keep these scripts aligned with the delivered behavior:
- `scripts/build_win.bat`
- `scripts/build_start_win.bat`
- `scripts/build_win.sh`
- `scripts/build_start_win.sh`
- For packaged artifacts, verify required directories exist:
- `lib`
- `assets`
- `conf`
- `data`
- `local_data`
- `lang`
- `definition`
- Ensure the packaged root remains minimal and includes the DB cleanup script when release packaging is in scope.
- For deployment target `C:\Program Portable\MindNavigator\`, use `assets/icon.ico`.

## Command Map
### Navigation
- Find files: `rg --files`
- Find symbol or text: `rg -n "<pattern>" mindnavigator tests`

### Validation
- Syntax check: `python -m compileall mindnavigator main.py`
- Focused tests: `pytest tests -k <scope>`
- Full tests, env-safe: `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

### Build Triggers
- `b_start`: build, compile, place into `C:\Program Portable\MindNavigator\`, then run.
- `b_build`: build, compile, place into `C:\Program Portable\MindNavigator\`, without run.

### Git Hygiene
- Status: `git status --short`
- Diff summary: `git diff --stat`
- Changed files: `git diff --name-only`

## Finish Checklist
- Only task-related files were changed.
- No accidental behavioral changes were introduced in the desktop flow.
- `python -m compileall mindnavigator main.py` passed for code changes.
- Focused tests for the changed scope passed, or the limitation is documented.
- Windows-specific logic remains guarded by `sys.platform == "win32"`.
- Storage changes include migration plus read and write path updates.
- The final summary includes changed files, validation results, and residual risks.

## Done Criteria
- Code compiles.
- Relevant tests pass, or the reason they were not run is stated explicitly.
- The final report explains what changed, why it changed, how it was validated, and what risk remains.

## Supporting References
- `.codex/CHECKLIST.md` and `.codex/COMMANDS.md` remain as quick-reference companions.
- `.codex/rules/*.md` remain as modular rule sources for audit and reuse.
- `.codex/skills/mindnavigator-routine/SKILL.md` should stay aligned with this file because it is the enabled project skill in `.codex/config.toml`.
