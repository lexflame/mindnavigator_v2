---
name: mindnavigator-routine
description: Routine workflow for bug fixes, small features, targeted refactors, tests, and release prep in this repository.
---

# Skill: mindnavigator-routine

## When To Use
Use this skill for routine repository work in `mindnavigator_v2`: bug fixes, small features, targeted refactors, tests, and release preparation.

## Rule Priority
1. Direct task request.
2. `.codex/AGENTS.md`.
3. `.codex/SKILL.md`.
4. This file.

## Core Scope
- Work only inside the current repository.
- Keep changes minimal, task-scoped, and reversible.
- Preserve stable desktop behavior unless the task explicitly requires behavior changes.
- Preserve backward compatibility unless the task explicitly requires a breaking change.

## Default Flow
1. Inspect Git state with `git status` and `git branch --show-current`.
2. Create a dedicated task branch before editing; do not work directly in protected or shared branches.
3. If uncommitted user changes exist, stop and ask for instructions.
4. Discover scope with `rg`.
5. Read impacted modules and call sites.
6. Implement the minimal in-place patch.
7. Validate the changed scope.
8. If manual testing is required, stop after reporting automated results and wait for user confirmation before creating a PR.
9. Return a concise summary with changed files, validation results, and residual risks.

## Validation Gates
- For code changes, run `python -m compileall mindnavigator main.py`.
- Run focused tests: `PYTHONPATH=. pytest tests -k <scope>`.
- If tests are not run, say why.
- If storage schema changes, validate migration plus read and write paths together.
- If UI behavior changes, validate the affected interaction path with a test or an explicit manual verification note.

## Sprint And Release Extension
Apply only when the task is explicitly sprint, release, parity, or hotfix work.
1. Assign `TASK_GUID`.
2. Update `.codex/HISTORY_TASK.md`.
3. Append meaningful entries to `.codex/HISTORY_ACTION.md`.
4. Work in a dedicated sprint branch.
5. Use one task-focused commit when commits are requested.
6. If commits are requested, use prefixes:
- feature: `feat//:: TASK_GUID`
- fix: `fix//:: TASK_GUID`
- parity: `parity::// TASK_GUID`
7. Push only after successful validation and only when requested or required.

## Build And Trigger Notes
- Keep build scripts aligned when release scope is part of the task.
- `b_start`: build, compile, deploy to `C:\Program Portable\MindNavigator\`, and run.
- `b_build`: build, compile, deploy to `C:\Program Portable\MindNavigator\`, without run.

## Constraints
- No unrelated edits.
- No destructive file operations unless explicitly requested.
- Keep architecture and naming consistent with nearby code.
- Prefer deterministic logic over implicit side effects.

## Done Criteria
- Code compiles.
- Relevant tests pass, or the reason they were not run is stated explicitly.
- The final response includes changed files, validation results, and residual risks.
