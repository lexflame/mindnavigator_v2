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
| `P3-05` | `codex/task-delegate-metrics` | текущий HEAD | Кэшированы стабильные font/layout metrics и цветные priority icons; повторные expanded size hints ускорены без кэширования state-зависимых прямоугольников. |

## Текущая работа

- Пункт: `P3-06` — проверка памяти карт, изображений и коллекций.
- Ветка: `codex/task-delegate-metrics`.
- Статус: `P3-05` завершён.
- Проверки `P3-05`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_tasks_delegate_metric_cache.py tests/test_run_perf_benchmarks.py tests/test_tasks_marker_refresh.py tests/test_view_menu_geometry.py tests/test_tasks_workspace_mn202.py -k "delegate or size_hint or sizehint or layout or header_quick or project_type or parent_schedule" -q -p no:cacheprovider --basetemp .pytest_dir/p3_05_focused` — `23 passed, 97 deselected`;
  - benchmark 5k, 10 итераций/2 warmup: `tasks_delegate_size_hints p95 = 14.530 ms`; ручной повторный проход 3931 expanded rows: `678.675 → 243.308 ms`.

## Следующий шаг

После ручной проверки высоты раскрытых строк при изменении ширины списка и темы создать отдельную ветку от `codex/task-delegate-metrics` и начать `P3-06`: измерить память процесса при повторном открытии/закрытии карт, изображений и коллекций, затем исправлять только подтверждённое удержание объектов или pixmap-кэшей.
