# AGENTS.md (Repo Template)

## Purpose
Compact repository template for a Codex pack that uses a consolidated model:
- local `.codex/AGENTS.md` as the source of truth,
- repository root `AGENTS.md` as a compatibility bridge,
- local `.codex/SKILL.md` as the main workflow file.

## Recommended Rule Priority
1. Direct task request.
2. `.codex/AGENTS.md`.
3. `.codex/SKILL.md`.
4. Other supporting `.codex` reference files.

## Template Working Rules
- Deliver minimal, correct, reversible changes.
- Keep patches task-scoped and avoid unrelated rewrites.
- Preserve stable product behavior unless the task explicitly requires a behavior change.
- Preserve backward compatibility unless the task explicitly requires a breaking change.
- Search first, then inspect call sites, then patch in place.
- Validate changed behavior before the final response.

## Template Validation Contract
- For code changes, run a syntax pass first.
- Run focused tests for the changed scope.
- If tests were not run, say why.
- Report changed files, validation commands, outcomes, and residual risks.

## Template Sprint And Release Rules
Apply only when the task is explicitly sprint, release, parity, or hotfix work.
- Use a dedicated sprint branch.
- Track `TASK_GUID` in the task history file.
- Log meaningful actions in the action history file.
- Prefer one focused commit per task when commits are requested.
- Use explicit commit prefixes for feature, fix, and parity work.
- Push only after successful validation and only when requested or required by the delivery flow.

## Template File Roles
- `.codex/AGENTS.md`: authoritative repository policy.
- `AGENTS.md`: compatibility bridge for root-level autodiscovery.
- `.codex/SKILL.md`: primary local workflow.
- `.codex/COMMANDS.md`: quick command reference.
- `.codex/CHECKLIST.md`: finish checklist.
- `.codex/rules/*.md`: modular source rules for audit and reuse.
