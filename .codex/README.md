# CODEX CLI Config Pack

This folder contains the active Codex support pack for productive work in this repository.
The workflow was consolidated so the main execution guidance now lives in `.codex/SKILL.md`, while the other files remain supporting references, templates, and configuration assets.

## Files
- `AGENTS.md`: policy and guardrails for Codex.
- `SKILL.md`: primary workflow and execution guidance for repository tasks.
- `COMMANDS.md`: quick command and trigger reference.
- `CHECKLIST.md`: quick pre-finish quality checklist.
- `config-basic.toml`: baseline Codex CLI settings.
- `config-advanced.toml`: advanced overlay and includes.
- `profiles/mcp.toml`: MCP server profile template.
- `profiles/multi-agent.toml`: multi-agent profile template.
- `rules/*.md`: modular source rules kept for audit and reuse.
- `AGENTS.repo.md`: concise AGENTS.md template.
- `skills/mindnavigator-routine/SKILL.md`: active local skill referenced by `.codex/config.toml`, kept aligned with `.codex/SKILL.md`.
- `multi-agent-playbook.md`: role split and handoff contract.

## Recommended Setup
1. Keep repository-level rules in the root `AGENTS.md` as the source of truth.
2. Use `.codex/SKILL.md` as the primary workflow source inside the local Codex pack.
3. Keep `skills/mindnavigator-routine/SKILL.md` aligned with `.codex/SKILL.md`, because it is the enabled project skill in `.codex/config.toml`.
4. Treat `rules/*.md`, `COMMANDS.md`, and `CHECKLIST.md` as supporting reference modules, not the primary workflow source.
5. Copy `config-basic.toml` to `%USERPROFILE%\.codex\config.toml` as a starting point when creating an external user-level setup.
6. For extended setup, merge `config-advanced.toml` and enable needed profiles.

## Operational Principle
- Minimal diffs.
- Focused verification first.
- Zero unrelated edits.
- Stable desktop behavior first.
