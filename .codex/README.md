# CODEX CLI Config Pack

This folder contains a ready-to-use configuration pack for productive work in this repository.
It now includes extended templates aligned with Codex docs: config basic/advanced, rules, agents, skills, MCP, and multi-agent.

## Files
- `AGENTS.md`: policy and guardrails for Codex.
- `SKILL.md`: execution workflow for routine tasks.
- `COMMANDS.md`: fast command/trigger map.
- `CHECKLIST.md`: pre-finish quality checklist.
- `config-basic.toml`: baseline Codex CLI settings.
- `config-advanced.toml`: advanced overlay + includes.
- `profiles/mcp.toml`: MCP server profile template.
- `profiles/multi-agent.toml`: multi-agent profile template.
- `rules/*.md`: portable rule files.
- `AGENTS.repo.md`: concise AGENTS.md template.
- `skills/mindnavigator-routine/SKILL.md`: reusable local skill.
- `multi-agent-playbook.md`: role split and handoff contract.

## Recommended Setup
1. Keep repository-level rules in the root `AGENTS.md` as the source of truth.
2. Copy `config-basic.toml` to `%USERPROFILE%\.codex\config.toml` as a starting point.
3. For extended setup, merge `config-advanced.toml` and enable needed profiles.
4. Sync `rules/*.md` into `.codex/rules/` for project-level behavioral constraints.
5. Reuse `skills/mindnavigator-routine/SKILL.md` as a local skill scaffold.
6. Use `COMMANDS.md` as standard trigger aliases during sessions.
7. Run `CHECKLIST.md` before finalizing significant changes.

## Operational Principle
- Minimal diffs.
- Focused verification first.
- Zero unrelated edits.
- Stable desktop behavior first.
