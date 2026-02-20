# AGENTS.md

## Project profile
- Name: mindnavigator_v2
- Language: Python 3.11+
- Primary entrypoint: `main.py`
- Main packages: `mindnavigator/`, `tests/`

## Objectives
- Keep desktop app behavior stable.
- Prefer minimal, targeted changes over broad refactors.
- Preserve backward compatibility unless task explicitly requires breaking changes.

## Workflow defaults
- Before edits: inspect related files and search usages.
- After edits: run focused checks first, then broader checks when needed.
- Prefer fast search tools (`rg`) for code navigation.

## Code style
- Follow existing style in touched files.
- Use clear names and small functions.
- Add comments only for non-obvious logic.
- Avoid unnecessary dependencies.

## Validation
- Run focused tests for changed modules first: `pytest tests -k <scope>`.
- If no tests exist for a change, add or update at least one relevant test where practical.
- For syntax validation use: `python -m compileall mindnavigator main.py`.

## Safety rules
- Do not rewrite unrelated files.
- Do not remove user data paths/configs unless explicitly requested.
- Keep file operations conservative and reversible.

## Skill loading
- Use local project skill from `.codex/SKILL.md` when task matches routine project work.
- If instructions conflict, this file has priority for repository-level behavior.
