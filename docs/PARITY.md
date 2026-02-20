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

### TASK_3EE8F658-4E55-4A52-A2A7-6A7ACCB1D0F0
- Type: parity
- Title: Review unexpected file `.codex/manual/ERROR_GIT/git_runner.txt`
- Sprint: 1
- Status: Planned
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
