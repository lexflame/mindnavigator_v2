# Multi-Agent Playbook

## Recommended Split
1. `explorer`: gathers code context and file map.
2. `worker`: implements patch and runs focused validation.
3. `reviewer`: checks regressions, edge cases, and missing tests.

## Handoff Contract
- Explorer output: exact file paths and risk notes.
- Worker output: patch summary and test/compile outputs.
- Reviewer output: prioritized findings by severity.

## Stop Conditions
- Conflicting edits in same region.
- Failing focused validation.
- Unclear behavior contract from caller.
