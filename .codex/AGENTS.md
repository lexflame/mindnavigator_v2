# AGENTS.md (Codex Pack Policy Mirror)

## Purpose
Concise policy mirror for the local Codex support pack in `mindnavigator_v2`.
This file is a compact policy layer inside `.codex`; the authoritative repository rules remain in the root `AGENTS.md`, and the main execution workflow inside the Codex pack lives in `.codex/SKILL.md`.

## Rule Priority
1. Direct task request.
2. Repository root `AGENTS.md`.
3. `.codex/SKILL.md`.
4. This file.
5. Other supporting files inside `.codex/`.

## Core Policy
- Keep changes minimal, task-scoped, and reversible.
- Preserve stable desktop behavior unless the task explicitly requires behavior changes.
- Preserve backward compatibility unless the task explicitly requires a breaking change.
- Do not modify unrelated files.
- Do not remove user data or config paths unless explicitly requested.
- Validate changed behavior before the final response.

## Repository-Specific Guardrails
- Use `rg` first for navigation and impact discovery.
- Inspect call sites before changing public behavior.
- Keep Windows-only logic guarded by `sys.platform == "win32"`.
- Use timezone-aware UTC with `datetime.now(timezone.utc)`.
- Use Qt6 enums and keep model `data()` signatures compatible.
- Prefer delegate-based hit zones for quick row actions over embedded widgets.
- For new persisted fields, update schema or migration, dataclasses, CRUD SQL, model roles, dialogs, and delegate painting together.
- For task reparent or move logic, resolve the project from the top-most parent chain before the DB update.
- Runtime settings should persist in storage and apply live in `MainWindow` when practical.
- Single-instance activation should send a lightweight restore signal and then exit.

## Validation Baseline
- For code changes, run `python -m compileall mindnavigator main.py`.
- Run `pytest tests -k <changed_scope>` for changed behavior.
- If tests are not run, state why.
- Report validation commands, outcomes, and residual risks.

## Sprint And Release Policy
Apply only for explicit sprint, release, parity, or hotfix work.
- Use a dedicated sprint branch.
- Track `TASK_GUID` in `.codex/HISTORY_TASK.md`.
- Append meaningful actions to `.codex/HISTORY_ACTION.md`.
- Use one focused commit per task when commits are requested.
- If commits are requested, use these prefixes:
- feature: `feat//:: TASK_GUID`
- fix: `fix//:: TASK_GUID`
- parity: `parity::// TASK_GUID`
- Push only after successful validation and when requested or required by the delivery flow.

## Supporting References
- `.codex/SKILL.md`: primary workflow and execution flow.
- `.codex/COMMANDS.md`: quick command map.
- `.codex/CHECKLIST.md`: finish checklist.
- `.codex/rules/*.md`: modular source rules kept for audit and reuse.
