# TASK_6F5C2E91-0D7A-4D33-A6C0-1E5F8D0B9A11 Plan

## Scope
- Move `mindnavigator/sprint_parser.py`, `mindnavigator/sprint_composer.py`, and `mindnavigator/sprint_classification.py` into `mindnavigator/transfer/sprint/`.
- Preserve old imports via thin compatibility modules on the historical paths.
- Update `docs/diagramm/` to reflect the new transfer package layout and dependency flow.

## Dependencies
- Mutual imports between sprint parser, composer, and classification modules.
- Tests: `tests/test_sprint_parser.py`, `tests/test_sprint_composer.py`, `tests/test_sprint_classification.py`.
- Any source maps in `docs/diagramm/` that still point to the legacy top-level files.

## Validation
- `python -m compileall mindnavigator main.py`
- `pytest tests/test_sprint_parser.py tests/test_sprint_composer.py tests/test_sprint_classification.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp`

## Rollback Notes
- Remove `mindnavigator/transfer/sprint/` package.
- Restore full implementations in the original top-level sprint modules.
- Revert diagram updates that reference the new package.
