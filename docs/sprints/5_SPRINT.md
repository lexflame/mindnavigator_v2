# Sprint 5: Debug And Static Analysis Hygiene

## Sprint Goal
Stabilize code quality after feature delivery by fixing PyCharm static-analysis issues, normalizing Qt6 API usage, and documenting durable coding rules for future changes.

## Scope
- Primary target: `mindnavigator/workspaces/*.py`, shared diagnostics workflow, and sprint-level engineering rules.
- Include targeted cleanups for warnings observed during active development in PyCharm.
- Out of scope: broad feature redesign outside already implemented sprint items.

## Task List
1. `TASK_GUID: TASK_5D4A1E18-B73B-4A86-9B22-8AB0B0F62A11` - Preparation maps
- Build/update maps used by agents and skills:
  `docs/CLASS.md`, `docs/INTERFACE.md`, `docs/DIALOG.md`, `docs/PROPERTY.md`, `docs/LIVE.md`.

2. `TASK_GUID: TASK_0C0B9E9A-CE9D-4C22-B15E-2C90B8559E2E` - Feature additions verification/fix pass
- Validate delivered additions for Tasks/Projects/Settings in code and behavior.
- Ensure no regression in project/task quick actions and nesting logic.

3. `TASK_GUID: TASK_BDF6F1F6-73E0-4D8D-AB8D-4EAA8E5ABF90` - Deprecation and API compatibility cleanup
- Replace deprecated UTC usage (`datetime.utcnow`) with timezone-aware UTC.
- Normalize Qt5-style constants to Qt6 enum paths across workspaces.

4. `TASK_GUID: TASK_E83A0F89-B1C2-4B6D-8F9D-36B44A9B6366` - PyCharm diagnostics remediation
- Fix unresolved attribute references.
- Fix signature mismatches (`QAbstractItemModel.data`).
- Fix broad exception clauses where clearly over-scoped.
- Fix naming/shadowing issues reported by inspection.

5. `TASK_GUID: TASK_B6C1869A-4B17-41B5-8DFA-8B4C80A3C4E7` - Team coding guardrails
- Record enforceable hygiene rules in `AGENTS.md` from real warning patterns.

6. `TASK_GUID: TASK_D97773B0-08F9-4A3B-9D0F-FA374D4E15E4` - Validation and test execution
- Compile check for modified modules.
- Run full/targeted pytest with environment-specific fallback when tmpdir ACL issues occur.

## Definition of Done
- PyCharm warning classes addressed in touched workspace files.
- Qt6 enum conventions and model signatures aligned in edited code.
- `AGENTS.md` updated with explicit static-analysis hygiene rules.
- Compile pass succeeds for workspace modules.
- Test result captured with transparent note about environment constraints.

## Execution Notes
- Created batch helpers to fix local ACL issues impacting pytest temp roots:
  `fix_pytest_permissions.bat`, `fix_pytest_user_temp_permissions.bat`.
- Full pytest run in current environment still fails at tmpdir cleanup due external ACL behavior.
- Stable fallback run completed:
  `37 passed, 1 deselected` with `-p no:tmpdir` and excluding `test_persistence_round_trip`.

## Release Summary
- Static-analysis hygiene pass completed for workspace layer.
- Sprint-level coding rules documented to reduce recurrence of the same warning classes.
- Remaining blocker is environment-specific pytest tmpdir permission behavior, not functional regressions in workspace logic.
