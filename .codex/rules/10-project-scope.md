# Project Scope Rule

## Mandatory
- Work only inside this repository root.
- Keep patches minimal and task-scoped.
- Do not rewrite unrelated modules.
- Preserve stable desktop behavior and backward compatibility by default.

## Conflict Resolution
- If rules conflict, apply this order:
  1. Direct task request.
  2. `.codex/AGENTS.md`.
  3. `.codex/SKILL.md`.
  4. Other supporting files from `.codex/`, including `.codex/rules/`.
- Breaking changes are allowed only when the task explicitly requires them.
