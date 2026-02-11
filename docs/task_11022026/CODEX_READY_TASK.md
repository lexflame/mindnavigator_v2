# CODEX_READY TASK: Batch implementation pack (task_11022026)

## Контекст
Этот документ — готовая входная задача для CODEX, собранная из `codex_tasks_index.md` и вложенных `CODEX_TASK_*.md` в каталоге `docs/task_11022026`.

## Режим выполнения
1. Выполняй задачи строго по приоритету (от TASK-001 к TASK-014).
2. Для каждой задачи используй соответствующий файл-спецификацию из колонки **Spec File**.
3. Внутри каждой спецификации выполняй шаги последовательно: Step 1 → review/diff → Step 2 → ...
4. После завершения каждой задачи:
   - прогони релевантные проверки/тесты;
   - зафиксируй изменения отдельным commit;
   - обнови статус в этом документе (Done/In Progress/Todo).
5. Не объединяй несколько задач в один commit, если это не требуется явно.

## Ready queue

| Priority | Task ID | Task | Spec File | Status |
|---|---|---|---|---|
| 1 | TASK-001 | Persist Task Edit Form Size | `docs/task_11022026/CODEX_TASK_TaskEditForm_PersistSize.md` | Todo |
| 2 | TASK-002 | Collections Workspace | `docs/task_11022026/CODEX_TASK_CollectionsWorkspace.md` | Todo |
| 3 | TASK-003 | Link parsing in description | `docs/task_11022026/CODEX_TASK_TaskDescription_LinkParsing.md` | Todo |
| 4 | TASK-004 | Ctrl+Enter saves form | `docs/task_11022026/CODEX_TASK_TaskEditForm_CtrlEnterSave.md` | Todo |
| 5 | TASK-005 | Periodic tasks scheduler | `docs/task_11022026/CODEX_TASK_PeriodicTasks_Scheduler.md` | Todo |
| 6 | TASK-006 | Project properties defaults/bindings | `docs/task_11022026/CODEX_TASK_ProjectProperties_DefaultsAndBindings.md` | Todo |
| 7 | TASK-007 | Double-click parent expands subtasks | `docs/task_11022026/CODEX_TASK_Tasks_DoubleClickParentExpands.md` | Todo |
| 8 | TASK-008 | Nested subprojects + wider panel | `docs/task_11022026/CODEX_TASK_Projects_NestedSubprojects_AndWiderPanel.md` | Todo |
| 9 | TASK-009 | Hide standard window header (frameless) | `docs/task_11022026/CODEX_TASK_UI_FramelessForms_HideHeader.md` | Todo |
| 10 | TASK-010 | Move-to-subtask inherits due datetime | `docs/task_11022026/CODEX_TASK_Subtasks_InheritDueOnMove.md` | Todo |
| 11 | TASK-011 | Label view redesign + note parsing | `docs/task_11022026/CODEX_TASK_Labels_ViewRedesign_AndNoteParsing.md` | Todo |
| 12 | TASK-012 | Map draw areas (grid) | `docs/task_11022026/CODEX_TASK_Maps_DrawGridAreas.md` | Todo |
| 13 | TASK-013 | Map draw paths | `docs/task_11022026/CODEX_TASK_Maps_DrawPaths.md` | Todo |
| 14 | TASK-014 | Marker visibility by zoom | `docs/task_11022026/CODEX_TASK_Maps_MarkerVisibility_ByZoom.md` | Todo |

## Универсальный промпт для запуска каждой задачи
Используй следующий шаблон при старте очередной задачи:

> Открой `<Spec File>` и выполни задачу пошагово (Step 1, Step 2, ...).  
> После каждого шага покажи diff и краткий отчёт, затем переходи к следующему шагу.  
> По завершении выполни тесты/проверки, сделай commit с осмысленным сообщением и обнови статус задачи.

## Источник
Сформировано на основе:
- `docs/task_11022026/codex_tasks_index.md`
- всех `docs/task_11022026/CODEX_TASK_*.md`
