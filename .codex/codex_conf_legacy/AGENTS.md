# AGENTS.md (Codex CLI Optimized)

## Scope
Repository development for `mindnavigator_v2` (Python 3.11+, desktop app).

## Priorities
1. Preserve app behavior and data safety.
2. Prefer minimal, targeted changes.
3. Keep backward compatibility unless task explicitly requires otherwise.

## Workflow
1. Locate affected code with `rg`.
2. Inspect call sites before editing.
3. Apply focused patch in-place.
4. Validate quickly:
   - `python -m compileall mindnavigator main.py`
   - `pytest tests -k <changed_scope>`
5. Report changed files, test results, and residual risks.

## Guardrails
- Do not modify unrelated files.
- Do not remove user data/config paths unless explicitly requested.
- Keep platform guards for Windows-specific behavior (`sys.platform == "win32"`).
- Use timezone-aware UTC (`datetime.now(timezone.utc)`), avoid deprecated UTC APIs.

## UI/Qt Rules
- Use Qt6 enums (`Qt.ItemDataRole.*`, `Qt.AlignmentFlag.*`, etc.).
- Keep model `data()` signatures compatible:
  `def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:`
- Prefer delegate-based hit zones for quick row actions over embedded widgets.

## Storage/Entity Rules
- For new persisted fields: update schema/migration + dataclasses + CRUD SQL + model roles + dialogs + delegate painting.
- For task reparent/move logic: resolve project from top-most parent chain before DB update.

## Runtime Settings Rules
- Persist setting to storage and apply live in `MainWindow` when practical.
- Single-instance activation should send lightweight restore signal and exit.
