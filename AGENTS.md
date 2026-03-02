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
- Add succinct comments or docstrings at key code paths and functions when the intent is not obvious and no explanation exists yet.
- Avoid unnecessary dependencies.

## Validation
- Run focused tests for changed modules first: `pytest tests -k <scope>`.
- If no tests exist for a change, add or update at least one relevant test where practical.
- For syntax validation use: `python -m compileall mindnavigator main.py`.

## Safety rules
- Do not rewrite unrelated files.
- Do not remove user data paths/configs unless explicitly requested.
- Keep file operations conservative and reversible.

## Git workflow rules
- Use credentials only from `.codex/git_key/` for Git operations in this repo.
- Default token source: `.codex/git_key/ghp_token` via `.codex/git_key/git_askpass.bat`.
- Before sprint work, create/switch to a dedicated branch named `sprint/<id_or_topic>`.
- For each `PARTITION` inside a sprint, create/switch to a dedicated branch before implementation (`sprint/<id_or_topic>-p<partition>` is the default shape).
- After each completed `PARTITION`, prepare a PR for that partition branch, complete/merge it only after required validations and pipeline checks pass, and then continue with the next partition.
- Before starting implementation for every sprint task, write a task decomposition that covers scope, dependencies, validation, and rollback notes.
- For each completed sprint task: make a commit and push branch updates.
- For every repository change, create a focused commit and push it after validation; do not batch unrelated edits into one commit.
- Before moving to the next sprint task, wait for the relevant pipeline to finish and verify it passed for the current branch/PR.

## Skill loading
- Use local project skill from `.codex/SKILL.md` when task matches routine project work.
- If instructions conflict, this file has priority for repository-level behavior.

## Debug Sprint recommendations (2026-02-24)
- For entity marker features (`marker_color`, `marker_theme`), always implement end-to-end:
  DB schema/migration in `mindnavigator/storage.py`, dataclasses, fetch/create/update SQL, model roles, edit dialogs, and delegate painting.
- When adding quick actions in list UIs, prefer delegate-based hit zones (`paint` + `editorEvent`) over embedded widgets for performance and minimal layout churn.
- Preserve parent/child consistency in task moves:
  reparenting to subtask must resolve project from the top-most parent chain before DB update.
- Settings that affect runtime behavior must be wired both ways:
  persist in `settings` table and emit/apply live changes in `MainWindow` without restart when practical.
- Windows-specific settings (`autostart`, single-instance restore) should stay guarded by `sys.platform == "win32"` and fail silently on registry/IPC errors.
- For single-instance behavior, keep external activation side-effect free:
  second process sends a lightweight `restore` message then exits.
- For UTC timestamps in storage layer, avoid deprecated `datetime.utcnow()`:
  use timezone-aware `datetime.now(timezone.utc)` and persist ISO strings.
- Keep list rendering width-sensitive changes localized to delegates/constants first (for example project path width in task rows) instead of broad UI rewrites.
- Validation order after edits:
  `python -m compileall mindnavigator main.py` first, then targeted pytest suites.
- Full suite validation command confirmed in this sprint:
  `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`.
- In this environment, pytest temporary directory permissions may fail unpredictably:
  use `PYTHONPATH=.` and run focused files if full-suite temp fixtures fail due ACL (`PermissionError` in pytest tmpdir internals).

## PyCharm hygiene rules (from debug pass)
- For Qt item roles, always use `Qt.ItemDataRole.*` instead of legacy `Qt.UserRole` / `Qt.DisplayRole`.
- For alignments and text flags, use Qt6 enums:
  `Qt.AlignmentFlag.*`, `Qt.TextElideMode.*`, `Qt.TextFlag.*`.
- For mouse/events/styles, use Qt6 enums:
  `Qt.MouseButton.*`, `QEvent.Type.*`, `QStyle.StateFlag.*`, `QPainter.RenderHint.*`, `Qt.DropAction.*`, `Qt.CursorShape.*`.
- For dialog result checks, use `QDialog.DialogCode.Accepted` (not `QDialog.Accepted`).
- In `QAbstractItemModel` descendants, keep `data()` signature compatible:
  `def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:`.
- For `QDialogButtonBox`, avoid bitwise constructor combinations that trigger type warnings:
  create box and add buttons explicitly via `addButton(QDialogButtonBox.StandardButton.*)`.
- Avoid protected cross-class calls (for example `obj._handle_*`); expose a public method for inter-object calls.
- Keep method argument names lowercase (`supported_actions`, not `supportedActions`).
- Avoid variable shadowing in nested scopes (`button`, `project`, etc.); prefer explicit names (`tab_button`, `project_row`, `node`).
- Replace deprecated UTC calls:
  use `datetime.now(timezone.utc)` instead of `datetime.utcnow()`.
