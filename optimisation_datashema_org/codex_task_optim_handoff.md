# Handoff: выполнение плана оптимизации

Актуально на: 2026-06-11

План: `optimisation_datashema_org/codex_task_optim_plan.md`

Базовая ветка исходного плана: `epic/tweaks_task_mode`

## Порядок работы

- Каждый следующий пункт выполняется в отдельной ветке, созданной от предыдущей завершённой ветки.
- Ветка содержит один сфокусированный коммит, обновление плана и относящиеся к пункту тесты.
- Для изменений Python выполняются `python -m compileall mindnavigator main.py` и целевые pytest-тесты.
- Этот файл обновляется при завершении каждого следующего пункта.

## Выполненные пункты

| Пункт | Ветка | Коммит | Результат |
| --- | --- | --- | --- |
| `P0-02` | `codex/task-domain-rules` | `d63acfd` | Описаны правила домена задач в `docs/task_domain_rules.md`. |
| `P1-03` | `codex/task-type-service` | `392db09` | Выделен `TaskTypeService`, добавлены интеграция и тесты. |
| `P1-05` | `codex/task-cascade-rollback-tests` | `7104dd8` | Каскады типов задач сделаны атомарными, добавлены rollback-тесты. |
| `P2-08` | `codex/haven-filter-model` | `80697ca` | Выделен независимый от Qt `HavenFilterState` с unit-тестами. |
| `P2-LINK-01` | `codex/entity-links-schema-proposal` | `4befb30` | Добавлен проект canonical-схемы `entity_links`. |
| `P2-01` | `codex/search-nav-debounce` | `22a57e5` | Добавлен debounce глобального поиска 200 мс и тесты. |
| `P1-UI-04` | `codex/shared-editable-list` | `32bab73` | Добавлен общий `EditableListWidget`, применённый в `ProjectEditDialog`. |
| `P3-01` | `codex/large-test-db-generator` | `1f70443` | Добавлен детерминированный генератор БД с проектами, задачами и context links. |
| `P2-02` | `codex/global-search-service` | `9f24c86` | Сбор результатов глобального поиска перенесён из `SearchNav` в независимый от Qt service. |
| `P3-02` (этап 1) | `codex/performance-benchmark-runner` | `5a52fa4` | Добавлен runner p50/p95 для `fetch_tasks` и глобального поиска; сохранён baseline 5k. |
| `P3-02` (этап 2) | `codex/tasks-model-reload-benchmark` | `15e0029` | Runner расширен измерением `TasksModel.refresh()` в offscreen Qt. |
| `P3-02` (этап 3) | `codex/form-open-benchmarks` | `1a8c6f8` | Добавлены offscreen-измерения конструирования `TaskEditDialog` и `ProjectEditDialog`; `P3-02` завершён. |
| `P2-LINK-02` | `codex/entity-links-read-facade` | `da3603a` | Добавлены `EntityRef`, `EntityLinkView` и единый read API поверх пяти legacy relation tables. |
| `P2-LINK-03` | `codex/entity-links-api-consumers` | `474a998` | Facade расширен связями персонажей, проектов и концептборда; панель связей заметки переведена на общий API. |
| `P2-LINK-04` | `codex/entity-incoming-links` | `6f3813c` | Во вкладке связей идеи добавлена read-only группа входящих связей с навигацией к источнику. |
| `P2-LINK-05` | `codex/entity-link-suggestions` | `6111285` | Добавлен детерминированный сервис suggested links и read-only предложения задач в карточке идеи. |
| `P2-LINK-06` | `codex/entity-link-drop-policy` | `a5074d7` | Добавлена единая policy допустимых link-drop пар и task drop target во вкладке связей идеи. |
| `P2-LINK-07` | `codex/linked-entities-widget` | `7aa1e1c` | Добавлен общий секционный компонент связанных сущностей; карточка идеи переведена на него. |
| `P2-03` | `codex/sqlite-fts5-search` | `c7b3d90` | Добавлены FTS5-индексы задач, идей, заметок и объектов, sync-триггеры и fallback-compatible интеграция глобального поиска. |
| `P2-04` | `codex/command-palette` | `feaa431` | `Ctrl+P` открывает palette команд и сущностей поверх общего search service с клавиатурной навигацией. |
| `P2-05` | `codex/search-result-actions` | `c14d01d` | Добавлен независимый registry быстрых действий; palette поддерживает переход к сущности и просмотр/редактирование карточки задачи. |
| `P2-06` | `codex/search-recents` | `a5c3afc` | В settings сохраняются ограниченные recent entities/actions; palette показывает их при пустом запросе. |
| `P2-07` | `codex/task-advanced-filters` | `28b541b` | Добавлены фильтры основной модели задач по типу, связям, отсутствию проекта и вложенности с сохраняемым UI-меню. |
| `P3-03` | `codex/performance-thresholds` | текущий HEAD (`perf: optimize task dialog reads`) | Зафиксированы UX-пороги; task dialog p95 на fixture 5k снижен до 225 мс узкими hierarchy-запросами, worker не потребовался. |
| `P3-04` | `codex/lazy-task-attachments` | `a511cf3` | Attachments summary переведён с N+1 на ленивую групповую выборку и кэш; частичная загрузка дерева отклонена по результатам измерения ниже UX-порога. |
| `P3-05` | `codex/task-delegate-metrics` | `55d3b7f` | Кэшированы стабильные font/layout metrics и цветные priority icons; повторные expanded size hints ускорены без кэширования state-зависимых прямоугольников. |
| `P3-06` | `codex/workspace-memory-smoke` | `4188f24` | Добавлен lifecycle/working-set smoke runner; карты, preview изображений и коллекции стабилизируются после прогрева и не оставляют живых владельцев. |
| `P1-TASK-FIX-01` | `fix/task-list-edit-route` | `e7cc1bd` | Редактирование из списка задач открывает актуальный `TaskDetailsDialog` сразу в режиме встроенного редактирования. |
| `P1-TASK-FIX-02` | `fix/task-create-enter-id` | `9866367` | Enter в полях формы создания обновляет временную задачу локально и не обращается к storage с `id=0`. |
| `P0-CODEX-01` | `codex/code-critic-role` | `c97beca` | Добавлен read-only custom agent `code_critic`, его конфигурация и документированный explicit-вызов. |
| `P1-TASK-FIX-03` | `fix/tasks-all-mode-contract` | текущий HEAD | Режим «Все» показывает все невыполненные и отложенные задачи без day-filter, сохраняет дерево и сортирует по дате/приоритету. |

## Текущая работа

- Пункт: `P0-DOC-01` — терминология и фактические контракты Форм СРП.
- Ветка: `fix/tasks-all-mode-contract`.
- Статус: `P1-TASK-FIX-03` завершён; требуется ручная проверка режима «Все».
- Проверки `P1-TASK-FIX-03`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_tasks_all_mode.py tests/test_tasks_workspace_mn202.py -k "all_mode or cycles_priority_including_deferred or secondary_modes_remain_available_outside_plan" -q -p no:cacheprovider --basetemp .pytest_dir/tasks_all_mode` — `4 passed`;
  - `python -m pytest tests/test_tasks_workspace_mn202.py tests/test_tasks_all_mode.py tests/test_task_advanced_filters.py -q -p no:cacheprovider --basetemp .pytest_dir/tasks_all_mode_full` — `100 passed`.

## Следующий шаг

Вручную проверить режим «Все»: навигация дня скрыта, задачи разных дат и отложенные видимы, выполненные скрыты, дочерние задачи раскрываются под родителем. Затем создать отдельную ветку и начать `P0-DOC-01`.
