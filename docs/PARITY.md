# PARITY Backlog

## Purpose
This file stores parity tasks that must be executed at the end of the sprint.
It also stores:
- tasks not completed within the sprint scope;
- tasks not solved during implementation;
- application improvement tasks.

## Rules
1. Every entry must have a `TASK_GUID`.
2. Commit prefix for parity tasks: `parity::// TASK_GUID`.
3. Status values: `Planned`, `In Progress`, `Done`, `Skipped`.
4. Each task must include clear acceptance criteria.

## Tasks

### TASK_5D95A5AE-2E6D-4A7B-9C4E-8F4C4E7A3B12
- Type: parity
- Title: Register Sprint 5 debug summary and environment constraint
- Sprint: 5
- Status: Done
- Why:
  Sprint 5 summary was created in `docs/sprints/5_SPRINT.md` and must be explicitly linked from parity tracking for end-of-sprint visibility.
- Scope:
  - add parity record with link to sprint summary;
  - capture test environment limitation (`pytest tmpdir` ACL cleanup issue on current machine).
- Acceptance criteria:
  - parity entry exists and references `docs/sprints/5_SPRINT.md`;
  - environment constraint is documented with current fallback test command.
- Result:
  - sprint summary file added: `docs/sprints/5_SPRINT.md`;
  - validated fallback test command in this environment:
    `PYTHONPATH=. pytest tests -q -p no:cacheprovider -p no:tmpdir -k "not test_persistence_round_trip"`
    with result `37 passed, 1 deselected`.

### TASK_3EE8F658-4E55-4A52-A2A7-6A7ACCB1D0F0
- Type: parity
- Title: Review unexpected file `.codex/manual/ERROR_GIT/git_runner.txt`
- Sprint: 1
- Status: Done
- Why:
  Unexpected file appeared during sprint execution and was not created intentionally in task flow.
- Scope:
  - determine origin of the file;
  - classify as needed artifact or accidental debug output;
  - decide keep/remove/ignore policy;
  - align git ignore rules if needed.
- Acceptance criteria:
  - file origin is documented;
  - clear decision is made (`keep`/`remove`/`ignore`);
  - repository state is consistent with decision.
- Result:
  - origin identified: file added by commit `4636c8d` (`CODEX ADDON FILE`);
  - classification: accidental debug output (CI lint error log), not product artifact;
  - decision: `remove` from repository and `ignore` path `.codex/manual/ERROR_GIT/`.

### TASK_CE3BF9F0-A286-4ED6-BD37-B250D90ECEDB
- Type: parity
- Title: Restore local automated test runner (`pytest`) in active Python environment
- Sprint: 1
- Status: Done
- Why:
  Multiple sprint tasks include tests, but runtime execution is blocked by missing dependency (`No module named pytest`).
- Scope:
  - install/enable `pytest` in active interpreter;
  - run dragdrop test suite end-to-end;
  - capture failures (if any) and create follow-up fix tasks.
- Acceptance criteria:
  - `python -m pytest tests/test_dragdrop_*.py -q` runs;
  - test execution report is recorded in `.codex/HISTORY_ACTION.md`;
  - any failing tests are tracked with new TASK_GUID entries.
- Result:
  - `pytest` installed (`pytest 9.0.2`);
  - dragdrop suite executed with `-p no:cacheprovider`;
  - discovered and fixed one regression in `tests/test_dragdrop_controller.py` related to frame throttling.

### TASK_5743A7F2-2D90-41A8-9D25-663435E0B526
- Type: parity
- Title: Fix throttling-related regression in clamp motion test
- Sprint: 1
- Status: Done
- Why:
  `test_controller_motion_clamps_max_step` failed after performance throttling was added.
- Scope:
  - make test deterministic under throttling;
  - rerun dragdrop suite.
- Acceptance criteria:
  - regression test passes;
  - full dragdrop suite passes.
- Result:
  - updated test to use `DragPerformanceConfig(min_render_interval_ms=0)`;
  - dragdrop suite: `23 passed`.
