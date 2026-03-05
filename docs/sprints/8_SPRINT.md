# Sprint 8: MindNavigator Integration Task Grammar And Execution Protocol

## Sprint Status
- Planned: 2026-03-05
- Source root: `MN-211`
- Source project: `MindNavigator / CODEX` (`project_id=24`)

## Sprint Goal
Build a deterministic integration workflow between Codex and MindNavigator where sprint tasks are parsed from MindNavigator titles and descriptions, decomposed by partition, and executed with explicit operator gates.

## Source Tree (MindNavigator)
- `MN-211` `# SPRINT :: Интеграционны спринт - Взаимодействие CODEX - MindNavigator`
- `MN-212` `## PARTITION :: Integration :: Опорные и ключевые слова для чтения задач`
- `MN-214` `TASK :: Словарь взаимодействия :: Сформировать словарь опорных слов`
- `MN-222` `TASK :: Формат строки заголовка задачи для парсинга из MindNavigator`
- `MN-213` `## PARTITION :: Integration :: Поведение для опорных слов eng. верхнего регистра значения`
- `MN-215` `TASK :: ## SPRINT`
- `MN-219` `ADDON :: Описание работы над опорным словом SPRINT`
- `MN-216` `TASK :: ## PARTITION`
- `MN-220` `ADDON :: Описание работы над опорным словом PARTITION`
- `MN-217` `TASK :: ## TASK`
- `MN-221` `ADDON :: Описание работы над опорным словом TASK`
- `MN-218` `TASK :: ## ADDON`
- `MN-223` `ADDON :: Описание работы над опорным словом ADDON`
- `MN-224` `## PARTITION :: Integration :: Поведение для опорных слов eng. нижнего регистра значения`
- `MN-225` `TASK :: ## Fix`
- `MN-226` `TASK :: ## Feat`
- `MN-227` `TASK :: ## Integration`
- `MN-228` `TASK :: ## Design`
- `MN-229` `TASK :: ## Workspace`
- `MN-230` `TASK :: ## Reafactor`
- `MN-231` `## PARTITION :: Integration :: Поведение для опорных слов rus. нижнего регистра значения`
- `MN-232` `TASK :: ## Фичи`
- `MN-233` `TASK :: ## Проработка`

## Operating Rules (From MN-211)
- Treat the external user as `operator` for this sprint workstream.
- Parse both task title and description from MindNavigator; do not rely on title only.
- Keep integration fail-safe and add integration self-check coverage.
- Use and update internal diagrams from `docs/diagramm/`.
- Keep `docs/PARITY.md` in sync during all sprint stages.
- Mark task completion in MindNavigator.
- Send operator notification in Telegram after each completed task.
- Add comments on key code paths and document classes/functions where intent is not obvious.
- When operator intervention is needed, generate `.bat` scripts under `scripts/codex_script/`.
- Execute partitions in order, then run PARITY backlog in order.
- Before sprint start, require operator confirmation.
- After PARITY, request operator build/test confirmation.
- After operator checks, request PyCharm inspection pass and address findings.
- After inspection fixes, prepare PR and release flow according to repository rules.

## Partitions
1. `PARTITION A` (`MN-212`): Lexicon and title parsing format.
2. `PARTITION B` (`MN-213`): Uppercase control-word semantics (`SPRINT`, `PARTITION`, `TASK`, `ADDON`).
3. `PARTITION C` (`MN-224`): Lowercase English task-type semantics (`Fix`, `Feat`, `Integration`, `Design`, `Workspace`, `Reafactor`).
4. `PARTITION D` (`MN-231`): Lowercase Russian abstraction semantics (`Фичи`, `Проработка`).

## Task Array
1. `MN-214`
- Type: `integration`
- Title: Build the canonical lexicon of control words.
- Partition: `PARTITION A`
- Scope: define canonical token set, aliases, typo-tolerant mapping.
- Dependencies: `MN-212`.
- Validation: parser unit tests for recognized/unrecognized tokens.
- Rollback: keep fallback to strict title parsing without aliases.

2. `MN-222`
- Type: `integration`
- Title: Define supported header line formats for task parsing.
- Partition: `PARTITION A`
- Scope: support full section format, full type format, and short format.
- Dependencies: `MN-214`.
- Validation: tests for all three formats and malformed separators.
- Rollback: keep previous parser behavior on unknown format.

3. `MN-215`
- Type: `integration`
- Title: Implement semantics for `SPRINT` header tasks.
- Partition: `PARTITION B`
- Scope: derive sprint brief from root `SPRINT` node title and description.
- Dependencies: `MN-214`, `MN-222`.
- Validation: end-to-end parse from root node to sprint brief payload.
- Rollback: treat `SPRINT` as plain task when semantic parse fails.

4. `MN-219`
- Type: `integration`
- Title: Apply `SPRINT` add-on behavior and decomposition guidance.
- Partition: `PARTITION B`
- Scope: allow decomposition and regrouping while preserving same root parent.
- Dependencies: `MN-215`.
- Validation: rule tests that included tasks belong to selected `SPRINT` root.
- Rollback: disable regrouping and keep direct hierarchy only.

5. `MN-216`
- Type: `integration`
- Title: Implement semantics for `PARTITION` nodes.
- Partition: `PARTITION B`
- Scope: build ordered sprint partitions from partition nodes.
- Dependencies: `MN-215`.
- Validation: deterministic ordering and partition description extraction tests.
- Rollback: flatten tasks into one backlog if partitioning fails.

6. `MN-220`
- Type: `integration`
- Title: Apply `PARTITION` add-on behavior for decomposition and gap-fill.
- Partition: `PARTITION B`
- Scope: support auto task synthesis when nested tasks are missing.
- Dependencies: `MN-216`.
- Validation: tests for both populated and empty partition branches.
- Rollback: disable auto-synthesis and keep partitions empty by default.

7. `MN-217`
- Type: `integration`
- Title: Implement semantics for leaf `TASK` nodes.
- Partition: `PARTITION B`
- Scope: build task briefs and keep MindNavigator IDs as rotation keys.
- Dependencies: `MN-216`.
- Validation: IDs are preserved in generated sprint artifacts.
- Rollback: fallback to generated local IDs with mapping table.

8. `MN-221`
- Type: `integration`
- Title: Apply `TASK` add-on behavior.
- Partition: `PARTITION B`
- Scope: allow task regrouping while preserving original MindNavigator numbering.
- Dependencies: `MN-217`.
- Validation: regrouping tests keep source node references intact.
- Rollback: disable regrouping and keep source order unchanged.

9. `MN-218`
- Type: `integration`
- Title: Implement semantics for `ADDON` nodes.
- Partition: `PARTITION B`
- Scope: treat addons as parent-task extensions for behavior/UX/rules.
- Dependencies: `MN-217`.
- Validation: parent-extension merge tests for task and partition levels.
- Rollback: keep addons as non-merged annotations.

10. `MN-223`
- Type: `integration`
- Title: Apply `ADDON` add-on processing rules.
- Partition: `PARTITION B`
- Scope: account for behavior, visual effects, free-form rules, and prototype hints.
- Dependencies: `MN-218`.
- Validation: addon parser tests by addon subtype.
- Rollback: process only plain-text addon notes without semantic merge.

11. `MN-225`
- Type: `fix`
- Title: Define `Fix` keyword behavior.
- Partition: `PARTITION C`
- Scope: route such tasks to bug/problem resolution workflow.
- Dependencies: `MN-214`, `MN-222`.
- Validation: classification tests route `Fix` tasks into fix queue.
- Rollback: route to generic integration type.

12. `MN-226`
- Type: `feat`
- Title: Define `Feat` keyword behavior.
- Partition: `PARTITION C`
- Scope: classify feature/rework requests into feature workflow.
- Dependencies: `MN-214`, `MN-222`.
- Validation: classification tests for feature and rework phrasing.
- Rollback: route to generic integration type.

13. `MN-227`
- Type: `integration`
- Title: Define `Integration` keyword behavior.
- Partition: `PARTITION C`
- Scope: classify integration tasks and set required dependency checks.
- Dependencies: `MN-214`, `MN-222`.
- Validation: classification and dependency-check gating tests.
- Rollback: route to generic feature workflow.

14. `MN-228`
- Type: `design`
- Title: Define `Design` keyword behavior.
- Partition: `PARTITION C`
- Scope: classify visual/interaction tasks and enforce UI review notes.
- Dependencies: `MN-214`, `MN-222`.
- Validation: tests confirm design-tagged tasks require UI acceptance notes.
- Rollback: keep design tasks in generic feature workflow.

15. `MN-229`
- Type: `workspace`
- Title: Define `Workspace` keyword behavior.
- Partition: `PARTITION C`
- Scope: classify workspace-level and nested-mode changes.
- Dependencies: `MN-214`, `MN-222`.
- Validation: tests for routing to workspace-specific checklist.
- Rollback: route to generic integration workflow.

16. `MN-230`
- Type: `refactor`
- Title: Define `Reafactor` keyword behavior.
- Partition: `PARTITION C`
- Scope: classify refactor/regression-recovery tasks.
- Dependencies: `MN-214`, `MN-222`.
- Validation: tests for both refactor and restoration semantics.
- Rollback: route to generic fix workflow.

17. `MN-232`
- Type: `feat`
- Title: Define `Фичи` abstraction behavior.
- Partition: `PARTITION D`
- Scope: map abstraction to adjacent feature behavior with parity handoff.
- Dependencies: `MN-214`, `MN-222`.
- Validation: tests confirm author-origin specifics are moved into PARITY.
- Rollback: process as plain feature without parity handoff.

18. `MN-233`
- Type: `chore`
- Title: Define `Проработка` abstraction behavior.
- Partition: `PARTITION D`
- Scope: map abstraction to extension/enrichment of existing functionality.
- Dependencies: `MN-214`, `MN-222`.
- Validation: tests confirm enhancement classification of active functionality.
- Rollback: process as generic integration task.

## Execution Order
1. `PARTITION A` (`MN-212`, `MN-214`, `MN-222`)
2. `PARTITION B` (`MN-213`, `MN-215..MN-223`)
3. `PARTITION C` (`MN-224`, `MN-225..MN-230`)
4. `PARTITION D` (`MN-231`, `MN-232`, `MN-233`)
5. PARITY pass
6. Operator build/test gate
7. Operator PyCharm inspection gate

## Validation Matrix
- Parser and classification changes:
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests -k entity_api -p no:cacheprovider`
- `PYTHONPATH=. pytest tests -k tasks -p no:cacheprovider`
- Integration self-check class:
- class-level unit tests for positive and negative parse cases
- end-to-end parse test from `MN-211` hierarchy snapshot
- Workflow artifacts:
- verify updates in `docs/diagramm/*` and `docs/PARITY.md`
- verify Telegram notification is sent after completed tasks

## Definition Of Done
- All `MN-211` descendant tasks are represented in sprint planning artifacts.
- Every sprint task has scope, dependencies, validation, and rollback notes.
- Partition order and operator gates are explicit and testable.
- PARITY handoff rules are defined for applicable keywords.
- Sprint plan is ready for execution under repository branch/PR/pipeline rules.
