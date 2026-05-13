# AGENTS.md

## Mandatory Rules
These rules are **mandatory** for any AI agent working in this repository.
The agent must not ignore or weaken them.

1. **Analyze first, edit second.** Read relevant code and usages before changing files.
2. **Minimal changes only.** Prefer focused patches over broad rewrites.
3. **Preserve architecture.** Do not mix UI, business logic, storage, and infrastructure layers.
4. **Preserve user behavior.** Keep desktop behavior stable unless the task explicitly requires a change.
5. **Preserve compatibility.** Do not break public interfaces/config formats/settings without explicit reason.
6. **No silent risky actions.** Destructive or system-level operations are forbidden unless explicitly requested.
7. **Validate changes.** Run the safest available checks and report exact commands and outcomes.

## Rule Priority
1. Direct task request.
2. This root `AGENTS.md`.
3. `.codex/SKILL.md` and active skill files.
4. Other `.codex/*` reference documents.

## Project Overview
- Project: `mindnavigator_v2`
- Language: `Python 3.11+`
- Desktop GUI: `PySide6` (Qt6)
- Primary entrypoint: `main.py`
- Package entrypoint: `python -m mindnavigator` via `mindnavigator/__main__/__init__.py`

## Application Architecture
- Entrypoints:
  - `main.py` (root launcher)
  - `mindnavigator/__main__/__init__.py` (app startup, splash, single-instance bridge)
- Core application package: `mindnavigator/`
- UI layer: `mindnavigator/ui/`, `mindnavigator/window/`, `mindnavigator/workspaces/`
- Storage/data layer: `mindnavigator/storage/` (SQLite + mixin-based database facade)
- Tests: `tests/`

### Architecture Guardrails
- Keep UI rendering and event handling in UI/workspace/delegate modules.
- Keep persistence and SQL logic in `mindnavigator/storage/`.
- Keep cross-layer changes explicit and minimal.
- For runtime settings, persist values in storage **and** apply live in `MainWindow` when practical.

## Tech Stack
- Python 3.11+
- PySide6 / Qt6
- SQLite storage layer in `mindnavigator/storage/`
- PyInstaller packaging (`pyinstaller.spec`, `scripts/build_*.bat`, `scripts/build_*.sh`)
- Test runner: `pytest` (`pytest.ini` present)

## Directory Structure
- `mindnavigator/` — application code
- `tests/` — automated tests
- `assets/` — UI assets
- `scripts/` — build and helper scripts
- `.codex/` — Codex configs, skills, and reference policy docs
- `docs/` — project documentation

## Development Rules
1. Prefer `rg` for navigation and usage discovery.
2. Do not rewrite unrelated files.
3. Do not remove user data paths/configs unless explicitly requested.
4. Avoid adding dependencies unless clearly justified.
5. Keep naming clear and local style consistent with touched files.
6. Add comments/docstrings only for non-obvious intent.
7. Avoid protected cross-class calls (`obj._handle_*`); expose public methods.
8. Avoid nested-scope variable shadowing.
9. Keep method argument names lowercase (`supported_actions`, not `supportedActions`).
10. For single-instance behavior, keep external activation side-effect free (`restore` message then exit).
11. Windows-specific runtime features (`autostart`, single-instance restore integration) must remain guarded by `sys.platform == "win32"` and fail silently on registry/IPC errors.

## Python Code Style
- Follow existing file-local style; do not introduce unrelated formatting churn.
- Keep functions small and purpose-focused.
- Prefer explicit imports and deterministic behavior.
- Do not wrap imports in try/catch blocks.
- For storage timestamps, avoid `datetime.utcnow()`; use `datetime.now(timezone.utc)` and persist ISO strings.

## UI Rules (Qt6)
1. Use `Qt.ItemDataRole.*` roles (not legacy `Qt.UserRole` / raw display-role constants).
2. Use Qt6 enum namespaces:
   - `Qt.AlignmentFlag.*`, `Qt.TextElideMode.*`, `Qt.TextFlag.*`
   - `Qt.MouseButton.*`, `QEvent.Type.*`, `QStyle.StateFlag.*`
   - `QPainter.RenderHint.*`, `Qt.DropAction.*`, `Qt.CursorShape.*`
3. Dialog result checks: use `QDialog.DialogCode.Accepted`.
4. `QAbstractItemModel.data()` compatibility signature:
   - `def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:`
5. For `QDialogButtonBox`, avoid bitwise constructor flag combinations; create the box then add buttons via `addButton(QDialogButtonBox.StandardButton.*)`.
6. For quick actions in list UIs, prefer delegate hit zones (`paint` + `editorEvent`) over embedded widgets.
7. Keep width-sensitive list rendering changes localized to delegates/constants first.

## Storage and Domain Integrity Rules
1. For entity marker features (`marker_color`, `marker_theme`), implement end-to-end:
   - schema/migration,
   - dataclasses,
   - fetch/create/update SQL,
   - model roles,
   - edit dialogs,
   - delegate painting.
2. For task reparent/move flows, resolve project from top-most parent chain before DB update.
3. Do not remove or silently alter persistent user settings formats.

## Configuration Rules
1. Root `AGENTS.md` is the repository source of truth.
2. `.codex/SKILL.md` is the primary local workflow companion and must stay aligned with this file.
3. Keep `.codex/config*.toml` coherent:
   - valid TOML syntax,
   - existing paths only,
   - no mutually exclusive defaults,
   - safe-by-default behavior.
4. Do not expose or modify secrets/tokens/credentials.
5. If an instruction file is template/reference-only, mark it clearly to avoid policy ambiguity.

## Testing and Validation
Use the safest available checks in this order.

### Required baseline (for code changes)
1. Syntax: `python -m compileall mindnavigator main.py`
2. Focused tests: `PYTHONPATH=. pytest tests -k <scope>`

### Full-suite option in this environment
- `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

### Tooling discovery status in this repository
- Present: `requirements.txt`, `pytest.ini`, `pyinstaller.spec`, build scripts in `scripts/`.
- Not configured in repo (no dedicated config found): `ruff`, `mypy`, `black`, `poetry`, `pipenv`, `make`.
- Do not invent replacement commands; document unavailable tools explicitly.

### Packaging checks (when packaging/build is in scope)
- Validate touched scripts:
  - `scripts/build_win.bat`
  - `scripts/build_start_win.bat`
  - `scripts/build_win.sh`
  - `scripts/build_start_win.sh`
- Preserve packaged directories used by scripts (`lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `defenition`).

## Safe Commands
The agent may run these commands when relevant:

- `rg --files`
- `rg -n "<pattern>" mindnavigator tests .codex`
- `python --version`
- `python -m pip list`
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests -k <scope>`
- `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`
- `git status --short`
- `git diff --stat`
- `git diff --name-only`

Always prefer read-only inspection commands before editing.

## Forbidden Actions
The agent must not, unless explicitly requested by the user:

1. Delete project files or user data paths without clear necessity.
2. Rewrite large parts of the app for a local/focused task.
3. Change binary assets unrelated to the task.
4. Modify virtual environments or perform system-wide package changes.
5. Install new dependencies without justification.
6. Change secrets/tokens/credentials or reveal sensitive values.
7. Run destructive commands (`rm -rf`, `del /s`, `format`, destructive disk/registry/system cleanup commands, etc.).
8. Silently ignore failed checks.
9. Invent project facts not present in the repository.
10. Push, merge, or rebase without explicit request.

## Git and Change Management
1. Keep one focused commit per task when commits are requested.
2. Do not batch unrelated edits.
3. Use credentials only from `.codex/git_key/` when authenticated Git operations are required.
4. For explicit sprint/release/parity/hotfix delivery:
   - use dedicated sprint branch naming,
   - track `TASK_GUID` in `.codex/HISTORY_TASK.md`,
   - append chronological actions to `.codex/HISTORY_ACTION.md`,
   - use commit prefixes:
     - `feat//:: TASK_GUID`
     - `fix//:: TASK_GUID`
     - `parity::// TASK_GUID`

## Before Editing
1. Confirm scope and non-goals from the user task.
2. Inspect related modules and call sites (`rg` + targeted file reads).
3. Identify architecture boundaries affected by the change.
4. Prepare a short task decomposition:
   - scope,
   - dependencies,
   - validation plan,
   - rollback notes.

## After Editing
1. Re-check changed files for scope drift.
2. Run safest applicable validations.
3. Record exact commands and outcomes.
4. If a check cannot run, state why (environment/tooling limitation) and residual risk.

## Done Criteria
A task is done only when all applicable conditions are satisfied:

1. Changes are minimal, relevant, and architecture-safe.
2. Required checks were executed successfully, **or** inability to run was explicitly justified.
3. No instruction conflicts remain in touched policy/config files.
4. Final report includes:
   - found issues,
   - changed files,
   - what was fixed,
   - validation commands and results,
   - residual risks,
   - final status (`ready`, `partially ready`, or `manual review required`).
