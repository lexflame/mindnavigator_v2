# AGENTS.md

## Purpose
Authoritative repository policy and Codex instruction file for `mindnavigator_v2`.
This file consolidates the repository-wide rules that previously lived in the root `AGENTS.md`
and the local Codex pack policy mirror. The root `AGENTS.md` now acts only as a compatibility
bridge that points here.

## Rule Priority
1. Direct task request.
2. This file: `.codex/AGENTS.md`.
3. `.codex/SKILL.md` and active skill files.
4. Other supporting `.codex/*` reference documents.

## Mandatory Rules
These rules are mandatory for any AI agent working in this repository.
The agent must not ignore or weaken them.

1. Analyze first, edit second. Read relevant code and usages before changing files.
2. Minimal changes only. Prefer focused patches over broad rewrites.
3. Preserve architecture. Do not mix UI, business logic, storage, and infrastructure layers.
4. Preserve user behavior. Keep desktop behavior stable unless the task explicitly requires a change.
5. Preserve compatibility. Do not break public interfaces, config formats, or settings without explicit reason.
6. No silent risky actions. Destructive or system-level operations are forbidden unless explicitly requested.
7. Validate changes. Run the safest available checks and report exact commands and outcomes.

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
- Storage and data layer: `mindnavigator/storage/` (SQLite + mixin-based database facade)
- Tests: `tests/`

### Architecture Guardrails
- Keep UI rendering and event handling in UI, workspace, and delegate modules.
- Keep persistence and SQL logic in `mindnavigator/storage/`.
- Keep cross-layer changes explicit and minimal.
- For runtime settings, persist values in storage and apply them live in `MainWindow` when practical.

## Tech Stack
- Python 3.11+
- PySide6 / Qt6
- SQLite storage layer in `mindnavigator/storage/`
- PyInstaller packaging (`pyinstaller.spec`, `scripts/build_*.bat`, `scripts/build_*.sh`)
- Test runner: `pytest` (`pytest.ini` present)

## Directory Structure
- `mindnavigator/` - application code
- `tests/` - automated tests
- `assets/` - UI assets
- `scripts/` - build and helper scripts
- `.codex/` - Codex configs, skills, and reference policy docs
- `docs/` - project documentation

## Development Rules
1. Prefer `rg` for navigation and usage discovery.
2. Do not rewrite unrelated files.
3. Do not remove user data paths or configs unless explicitly requested.
4. Avoid adding dependencies unless clearly justified.
5. Keep naming clear and local style consistent with touched files.
6. Add comments or docstrings only for non-obvious intent.
7. Avoid protected cross-class calls such as `obj._handle_*`; expose public methods instead.
8. Avoid nested-scope variable shadowing.
9. Keep method argument names lowercase (`supported_actions`, not `supportedActions`).
10. For single-instance behavior, keep external activation side-effect free (`restore` message then exit).
11. Windows-specific runtime features (`autostart`, single-instance restore integration) must remain guarded by `sys.platform == "win32"` and fail silently on registry or IPC errors.

## Python Code Style
- Follow existing file-local style; do not introduce unrelated formatting churn.
- Keep functions small and purpose-focused.
- Prefer explicit imports and deterministic behavior.
- Do not wrap imports in try or catch blocks.
- For storage timestamps, avoid `datetime.utcnow()`; use `datetime.now(timezone.utc)` and persist ISO strings.

## UI Rules (Qt6)
1. Use `Qt.ItemDataRole.*` roles, not legacy `Qt.UserRole` or raw display-role constants.
2. Use Qt6 enum namespaces:
   - `Qt.AlignmentFlag.*`, `Qt.TextElideMode.*`, `Qt.TextFlag.*`
   - `Qt.MouseButton.*`, `QEvent.Type.*`, `QStyle.StateFlag.*`
   - `QPainter.RenderHint.*`, `Qt.DropAction.*`, `Qt.CursorShape.*`
3. Dialog result checks must use `QDialog.DialogCode.Accepted`.
4. `QAbstractItemModel.data()` compatibility signature:
   - `def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:`
5. For `QDialogButtonBox`, avoid bitwise constructor flag combinations; create the box and add buttons via `addButton(QDialogButtonBox.StandardButton.*)`.
6. For quick actions in list UIs, prefer delegate hit zones (`paint` plus `editorEvent`) over embedded widgets.
7. Keep width-sensitive list rendering changes localized to delegates or constants first.

## Storage And Domain Integrity Rules
1. For entity marker features (`marker_color`, `marker_theme`), implement end-to-end:
   - schema or migration
   - dataclasses
   - fetch, create, and update SQL
   - model roles
   - edit dialogs
   - delegate painting
2. For task reparent or move flows, resolve project from the top-most parent chain before the DB update.
3. Do not remove or silently alter persistent user settings formats.

## Configuration Rules
1. `.codex/AGENTS.md` is the consolidated repository and Codex policy source.
2. The root `AGENTS.md` is a compatibility bridge and must stay aligned with this file.
3. `.codex/SKILL.md` is the primary local workflow companion and must stay aligned with this file.
4. Keep `.codex/config*.toml` coherent:
   - valid TOML syntax
   - existing paths only
   - no mutually exclusive defaults
   - safe-by-default behavior
5. Do not expose or modify secrets, tokens, or credentials.
6. If an instruction file is template-only or reference-only, mark it clearly to avoid policy ambiguity.

## Testing And Validation
Use the safest available checks in this order.

### Required Baseline (For Code Changes)
1. Syntax: `python -m compileall mindnavigator main.py`
2. Focused tests: `PYTHONPATH=. pytest tests -k <scope>`

### Full-Suite Option In This Environment
- `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

### Tooling Discovery Status In This Repository
- Present: `requirements.txt`, `pytest.ini`, `pyinstaller.spec`, build scripts in `scripts/`.
- Not configured in repo (no dedicated config found): `ruff`, `mypy`, `black`, `poetry`, `pipenv`, `make`.
- Do not invent replacement commands; document unavailable tools explicitly.

### Packaging Checks (When Packaging Or Build Is In Scope)
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
2. Rewrite large parts of the app for a local or focused task.
3. Change binary assets unrelated to the task.
4. Modify virtual environments or perform system-wide package changes.
5. Install new dependencies without justification.
6. Change secrets, tokens, or credentials, or reveal sensitive values.
7. Run destructive commands (`rm -rf`, `del /s`, `format`, destructive disk, registry, or system cleanup commands, and similar actions).
8. Silently ignore failed checks.
9. Invent project facts not present in the repository.
10. Push, merge, or rebase without explicit request.

## Git And Change Management
1. Keep one focused commit per task when commits are requested.
2. Do not batch unrelated edits.
3. Use credentials only from `.codex/git_key/` when authenticated Git operations are required.
4. For explicit sprint, release, parity, or hotfix delivery:
   - use dedicated sprint branch naming
   - track `TASK_GUID` in `.codex/HISTORY_TASK.md`
   - append chronological actions to `.codex/HISTORY_ACTION.md`
   - use commit prefixes:
     - `feat//:: TASK_GUID`
     - `fix//:: TASK_GUID`
     - `parity::// TASK_GUID`

## Git Branch And Pull Request Workflow
For every task started through Codex CLI, the agent must work in a separate Git branch.

### Mandatory Branch Workflow
1. Before making any changes, inspect the current Git state:
   - `git status`
   - `git branch --show-current`
2. The agent must not work directly in protected or shared branches, including but not limited to:
   - `main`
   - `master`
   - `develop`
   - `dev`
   - `release/*`
3. For each new task, create a new dedicated branch from the current base branch.
4. Branch names must be descriptive and use one of the following prefixes:
   - `codex/`
   - `feature/`
   - `fix/`
   - `chore/`
   - `docs/`
   - `refactor/`
5. Preferred branch naming format:
   - `codex/<short-task-name>`
   - examples: `codex/update-agents-config`, `codex/fix-python-desktop-startup`, `codex/refactor-settings-loader`
6. If there are uncommitted user changes before starting the task, the agent must not overwrite them.
7. If uncommitted user changes exist, the agent must report the existing changes and ask for explicit instructions before proceeding.
8. All code changes for the task must be committed only to the task branch.
9. The agent must keep changes minimal and related only to the current task.
10. The agent must not mix unrelated changes into the same branch.

### Testing Before Pull Request
Before preparing a pull request, the agent must run the safest available validation checks for the project.

The agent must determine available checks from the repository, including documented project commands such as:
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests -k <scope>`
- `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`
- project-specific commands from `README.md`, `pyproject.toml`, `Makefile`, or other documented sources when present

If a check cannot be run, the agent must document why.

The task branch must not be proposed for merge until:
- the required changes are complete
- available automated checks have been run
- the result of each check is reported
- the user has manually tested the result when manual testing is required

### User Manual Testing Gate
After Codex CLI finishes implementation and automated checks, it must stop and report:
- branch name
- changed files
- summary of changes
- commands and checks executed
- test results
- any risks or unresolved questions

Codex CLI must wait for the user's confirmation that manual testing was successful before creating a pull request.

Expected user confirmations may be phrased as:
- `Тестирование успешно, создай PR.`
- `Можно отправлять в PR.`

### Pull Request Creation
After successful user testing and explicit confirmation, Codex CLI must create a pull request from the task branch into the target base branch.

Preferred method:
- `git push --set-upstream origin <branch-name>`
- `gh pr create --base <base-branch> --head <branch-name> --title "<PR title>" --body "<PR description>"`

If GitHub CLI is unavailable or unauthenticated, Codex CLI must not fake pull request creation.

Instead, it must report the problem and provide the exact commands the user can run manually.

The pull request description must include:
- task summary
- list of important changes
- validation commands executed
- test results
- manual testing status
- known risks, if any

### Pull Request Restrictions
The agent must not:
1. Merge the pull request unless the user explicitly requests it.
2. Push directly to `main`, `master`, `develop`, `dev`, or release branches.
3. Force-push unless explicitly allowed by the user.
4. Create a pull request before tests or checks are run, unless the reason for skipping them is documented.
5. Create a pull request before the user confirms successful manual testing.
6. Include unrelated changes in the pull request.
7. Hide failing tests or unresolved problems.
8. Rewrite Git history without explicit permission.
9. Delete local or remote branches without explicit permission.

### Done Criteria
A Codex CLI task is complete only when one of the following is true:
1. The task branch is created, changes are committed, checks are reported, and the branch is ready for user testing.
2. After successful user testing and explicit confirmation, the branch is pushed and a pull request is created.
3. If pull request creation is impossible, the agent clearly reports why and provides manual commands for pushing the branch and creating the pull request.

## Before Editing
1. Confirm scope and non-goals from the user task.
2. Inspect related modules and call sites with `rg` plus targeted file reads.
3. Identify architecture boundaries affected by the change.
4. Prepare a short task decomposition:
   - scope
   - dependencies
   - validation plan
   - rollback notes

## After Editing
1. Re-check changed files for scope drift.
2. Run the safest applicable validations.
3. Record exact commands and outcomes.
4. If a check cannot run, state why and note the residual risk.

## Done Criteria
A task is done only when all applicable conditions are satisfied:

1. Changes are minimal, relevant, and architecture-safe.
2. Required checks were executed successfully, or the inability to run them was explicitly justified.
3. No instruction conflicts remain in touched policy or config files.
4. The final report includes:
   - found issues
   - changed files
   - what was fixed
   - validation commands and results
   - residual risks
   - final status (`ready`, `partially ready`, or `manual review required`)
