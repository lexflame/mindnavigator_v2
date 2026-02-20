# APP_DEVEL_AGENTS.md

## Purpose
Repository-level development policy for Codex agents.
This file defines mandatory constraints, quality gates, git policy, architecture, and release structure.

## Rule Allocation
This AGENTS file owns policy-level rules. Operational execution procedures are defined in `APP_DEVEL_SKILL.md`.

## Task Identity And History
- Every incoming task must receive a unique `TASK_GUID`.
- Task history must be maintained in `.codex/HISTORY_TASK.md`.
- Process I/O history must be maintained in `.codex/HISTORY_ACTION.md` in a chronological shell-history style similar to `.history_bash`.

## Branching And Commit Policy
- Each sprint must be developed in a dedicated sprint branch.
- Each task must be committed separately.
- If a fix is discovered during execution, create two commits in sequence:
  1. Commit the pre-fix (broken or incomplete) state.
  2. Commit the fix state.

## Commit Message Prefix Policy
- Feature/creation/implementation/development tasks: `feat//:: TASK_GUID`.
- Bug fixes: `fix//:: TASK_GUID`.
- Parity tasks: `parity::// TASK_GUID`.

## Testing Quality Gates
- Stable working automated tests must be present and verified.
- The repository must continuously maintain stable working automated tests.
- Before each commit, code must be tested.

## Git Operation Policy
- Use git keys from `.codex/git_key/` for repository git operations.
- After successful testing, push changes to git.

## Build And Packaging Policy
- Build/update `scripts/build_win.bat` for Win64.
- Build/update `scripts/build_start_win.bat` for Win64 build+compile flow.
- Build/update `scripts/build_win.sh` for *nix.
- Build/update `scripts/build_start_win.sh` for *nix build+compile flow.

## Compiled Application Structure
- Compiled application must include directories:
  `lib`, `assets`, `conf`, `data`, `local_data`, `lang`, `defenition`.
- Root of compiled application must contain a minimal file set.
- Root of compiled application must include a database cleanup script.

## Architecture Standard
- Use the MVP pattern for application development.
