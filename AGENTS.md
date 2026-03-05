# AGENTS.md

## Project Profile
- Name: `mindnavigator_v2`
- Language: `Python 3.11+`
- Primary entrypoint: `main.py`
- Main packages: `mindnavigator/`, `tests/`

## Unified Repository Rules
1. Keep desktop application behavior stable.
2. Prefer minimal, targeted changes over broad refactors.
3. Preserve backward compatibility unless the task explicitly requires a breaking change.
4. Before edits, inspect related files and search usages.
5. Prefer fast search tools (`rg`) for code navigation.
6. Do not rewrite unrelated files.
7. Do not remove user data paths or configs unless explicitly requested.
8. Keep file operations conservative and reversible.
9. Follow the existing style in touched files.
10. Use clear names and small functions.
11. Add comments only for non-obvious logic.
12. Add succinct comments or docstrings at key code paths and functions when the intent is not obvious and no explanation exists yet.
13. Avoid unnecessary dependencies.
14. For code changes, validate syntax with `python -m compileall mindnavigator main.py` before broader checks.
15. Run focused tests for changed modules first: `pytest tests -k <scope>`.
16. If no tests exist for a change, add or update at least one relevant test where practical.
17. After focused checks, run broader validation only when the scope justifies it.
18. Use credentials only from `.codex/git_key/` for Git operations in this repository.
19. Default token source is `.codex/git_key/ghp_token` via `.codex/git_key/git_askpass.bat`.
20. Before sprint work, create or switch to a dedicated branch named `sprint/<id_or_topic>`.
21. For each `PARTITION` inside a sprint, create or switch to a dedicated branch before implementation; the default shape is `sprint/<id_or_topic>-p<partition>`.
22. Before starting implementation for every sprint task, write a task decomposition that covers scope, dependencies, validation, and rollback notes.
23. For each completed sprint task, create a focused commit and push branch updates after validation.
24. For every repository change, create a focused commit and push it after validation; do not batch unrelated edits into one commit.
25. If commits are requested for explicit sprint or release work, use these commit prefixes:
- feature: `feat//:: TASK_GUID`
- fix: `fix//:: TASK_GUID`
- parity: `parity::// TASK_GUID`
26. For each completed `PARTITION`, open a dedicated PR for that partition branch.
27. Do not merge or complete a `PARTITION` PR until the required validations and pipeline checks pass.
28. Before moving to the next sprint task or `PARTITION`, wait for the relevant pipeline to finish and verify it passed for the current branch or PR.
29. Use the local project skill from `.codex/SKILL.md` when the task matches routine project work.
30. If instructions conflict, this file has priority for repository-level behavior.
31. For entity marker features (`marker_color`, `marker_theme`), implement end-to-end: DB schema or migration in `mindnavigator/storage.py`, dataclasses, fetch and create and update SQL, model roles, edit dialogs, and delegate painting.
32. When adding quick actions in list UIs, prefer delegate-based hit zones (`paint` plus `editorEvent`) over embedded widgets for performance and minimal layout churn.
33. Preserve parent and child consistency in task moves: reparenting to a subtask must resolve the project from the top-most parent chain before the DB update.
34. Settings that affect runtime behavior must be wired both ways: persist them in the `settings` table and emit or apply live changes in `MainWindow` without restart when practical.
35. Windows-specific settings (`autostart`, single-instance restore) must stay guarded by `sys.platform == "win32"` and fail silently on registry or IPC errors.
36. For single-instance behavior, keep external activation side-effect free: a second process sends a lightweight `restore` message and then exits.
37. In the storage layer, avoid deprecated `datetime.utcnow()`; use `datetime.now(timezone.utc)` and persist ISO strings.
38. Keep list-rendering width-sensitive changes localized to delegates or constants first instead of broad UI rewrites.
39. Preferred validation order after edits is `python -m compileall mindnavigator main.py` first, then targeted pytest suites.
40. A confirmed full-suite validation command for this environment is `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp`.
41. In this environment, pytest temporary-directory permissions may fail unpredictably; use `PYTHONPATH=.` and focused test files if full-suite temp fixtures fail with ACL-related `PermissionError`.
42. For Qt item roles, always use `Qt.ItemDataRole.*` instead of legacy `Qt.UserRole` or `Qt.DisplayRole`.
43. For alignments and text flags, use Qt6 enums: `Qt.AlignmentFlag.*`, `Qt.TextElideMode.*`, `Qt.TextFlag.*`.
44. For mouse and events and style enums, use Qt6 namespaces: `Qt.MouseButton.*`, `QEvent.Type.*`, `QStyle.StateFlag.*`, `QPainter.RenderHint.*`, `Qt.DropAction.*`, `Qt.CursorShape.*`.
45. For dialog result checks, use `QDialog.DialogCode.Accepted` and not `QDialog.Accepted`.
46. In `QAbstractItemModel` descendants, keep the `data()` signature compatible: `def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:`.
47. For `QDialogButtonBox`, avoid bitwise constructor combinations that trigger type warnings; create the box and add buttons explicitly via `addButton(QDialogButtonBox.StandardButton.*)`.
48. Avoid protected cross-class calls such as `obj._handle_*`; expose a public method for inter-object calls.
49. Keep method argument names lowercase, for example `supported_actions` and not `supportedActions`.
50. Avoid variable shadowing in nested scopes; prefer explicit names such as `tab_button`, `project_row`, and `node`.
51. For sprint decomposition from MindNavigator tasks, always read and use descriptions for the root task and all nested tasks; do not rely on titles only.
52. If operator confirmation is required before a meaningful action, send a Telegram notification request and continue only after confirmation is received.

## History File Rules
1. `HISTORY_TASK` source of truth is `.codex/HISTORY_TASK.md`.
2. `HISTORY_ACTION` source of truth is `.codex/HISTORY_ACTION.md`.
3. For explicit sprint, release, parity, or hotfix work, assign or confirm a `TASK_GUID` before implementation starts.
4. Before implementation starts for a tracked task, register the task in `.codex/HISTORY_TASK.md` if it is missing.
5. Every tracked task entry in `.codex/HISTORY_TASK.md` must include: `Task GUID`, sprint or workstream, title, type, and current status.
6. Update `.codex/HISTORY_TASK.md` whenever the task state changes, at minimum for: `Planned`, `In Progress`, `Blocked`, `Completed`, or an equivalent explicit terminal note.
7. Keep `.codex/HISTORY_TASK.md` append-friendly and audit-oriented: update statuses and add new rows or sections, but do not rewrite unrelated historical records.
8. Use `.codex/HISTORY_ACTION.md` as the chronological execution log for the current work.
9. Append new lines to `.codex/HISTORY_ACTION.md`; do not reorder or delete older entries unless the user explicitly asks for history cleanup.
10. Each `.codex/HISTORY_ACTION.md` entry should be timestamped and concise.
11. Log meaningful execution events in `.codex/HISTORY_ACTION.md`, including when relevant: session start, branch creation or switch, task start, task completion, key file additions or edits, validations, Git commands, PR creation, pipeline results, and merge completion.
12. When a command materially affects delivery, record both the command and its meaningful result in `.codex/HISTORY_ACTION.md`.
13. When a task status is changed in `.codex/HISTORY_TASK.md`, add a matching action entry in `.codex/HISTORY_ACTION.md` that explains the transition.
14. When a task is completed, ensure both history files agree: `.codex/HISTORY_TASK.md` must show the terminal status and `.codex/HISTORY_ACTION.md` must record what was delivered and how it was validated.
15. If work is not being tracked as an explicit sprint, release, parity, or hotfix task, updating the history files is optional unless the user asks for it.

## History Entry Templates
1. Use this strict line format for `.codex/HISTORY_ACTION.md`:
- `[YYYY-MM-DD HH:MM] TYPE: message`
2. `TYPE` in `.codex/HISTORY_ACTION.md` must be one of:
- `SESSION_START`
- `ACTION`
- `ANALYSIS`
- `CMD`
- `OUT`
- `ERROR`
3. For commands with meaningful execution output in `.codex/HISTORY_ACTION.md`, write them as two consecutive lines:
- `[YYYY-MM-DD HH:MM] CMD: <exact command or normalized command summary>`
- `[YYYY-MM-DD HH:MM] OUT: <meaningful result>`
4. For task state transitions in `.codex/HISTORY_ACTION.md`, use this strict line format:
- `[YYYY-MM-DD HH:MM] ACTION: Updated <TASK_GUID> status -> <STATUS>.`
5. For task start records in `.codex/HISTORY_ACTION.md`, use this strict line format:
- `[YYYY-MM-DD HH:MM] ACTION: Started <TASK_GUID> (<short title>).`
6. For task completion records in `.codex/HISTORY_ACTION.md`, use this strict line format:
- `[YYYY-MM-DD HH:MM] ACTION: Completed <TASK_GUID>.`
7. Use this strict Markdown table schema for `.codex/HISTORY_TASK.md` task rows:
- `| Task GUID | Sprint | Title | Type | Status |`
8. Each `.codex/HISTORY_TASK.md` row must use this strict row format:
- `| <TASK_GUID> | <SPRINT_OR_WORKSTREAM> | <TITLE> | <TYPE> | <STATUS> |`
9. `TYPE` in `.codex/HISTORY_TASK.md` should use repository work classes:
- `feat`
- `fix`
- `parity`
- `docs`
- `chore`
- `hotfix`
10. `STATUS` in `.codex/HISTORY_TASK.md` should use explicit workflow states:
- `Planned`
- `In Progress`
- `Blocked`
- `Completed`
- `Completed (<note>)`
11. Use this strict section header format for `.codex/HISTORY_TASK.md`:
- `## <Sprint Number or Workstream Name> - <Title>`
12. Immediately below each `.codex/HISTORY_TASK.md` section header, use this metadata block:
- `Created: YYYY-MM-DD`
- `Status: <SECTION_STATUS>`
