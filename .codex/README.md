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

## Role Inventory
### Source Of Truth
- Repository root `AGENTS.md`: authoritative repository policy and delivery rules.
- `.codex/SKILL.md`: authoritative workflow inside the local Codex pack.

### Active Runtime Files
- `.codex/config.toml`: active project Codex configuration for this repository.
- `.codex/skills/mindnavigator-routine/SKILL.md`: active local skill enabled by `.codex/config.toml`.

### Reference Files
- `.codex/AGENTS.md`: concise policy mirror for the local Codex pack.
- `.codex/COMMANDS.md`: quick command map.
- `.codex/CHECKLIST.md`: quick finish checklist.
- `.codex/rules/*.md`: modular source rules kept for audit and reuse.
- `.codex/multi-agent-playbook.md`: role split and handoff reference for multi-agent work.

### Template Files
- `.codex/AGENTS.repo.md`: reusable template for split-model Codex packs.
- `.codex/config-basic.toml`: baseline external Codex CLI config template.
- `.codex/config-advanced.toml`: overlay config template for extended setups.
- `.codex/profiles/mcp.toml`: MCP profile template.
- `.codex/profiles/multi-agent.toml`: multi-agent profile template.

### Operational Data
- `.codex/HISTORY_TASK.md`: task tracking log for explicit sprint, release, parity, and hotfix work.
- `.codex/HISTORY_ACTION.md`: chronological action log for tracked work.
- `.codex/git_key/`: local credential material for authenticated Git operations in this repository.

## Change Maintenance Rule
When the repository workflow, validation flow, sprint delivery flow, or history-tracking contract changes, keep these files aligned in the same change set:
1. Repository root `AGENTS.md` for authoritative policy.
2. `.codex/SKILL.md` for the primary local workflow.
3. `.codex/skills/mindnavigator-routine/SKILL.md` for the active runtime skill loaded by `.codex/config.toml`.
4. `.codex/AGENTS.md` and `.codex/AGENTS.repo.md` for the local policy mirror and template layer.
5. `.codex/CHECKLIST.md` and `.codex/COMMANDS.md` for quick-reference drift prevention.
6. `.codex/README.md` when file roles, rule priority, or pack structure changes.
7. `.codex/HISTORY_TASK.md` and `.codex/HISTORY_ACTION.md` when the change is explicit sprint, release, parity, or hotfix work.

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
