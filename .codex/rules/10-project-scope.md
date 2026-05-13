# Project Scope Rule

## Mandatory
- Work only inside this repository root.
- Keep patches minimal and task-scoped.
- Do not rewrite unrelated modules.
- Preserve stable desktop behavior and backward compatibility by default.

## Conflict Resolution
- If rules conflict, apply this order:
  1. Direct task request.
  2. Repository `AGENTS.md` in project root.
  3. Files from `.codex/rules/`.
- Breaking changes are allowed only when the task explicitly requires them.
