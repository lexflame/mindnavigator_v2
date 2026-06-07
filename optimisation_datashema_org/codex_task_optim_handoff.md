# Handoff: выполнение плана оптимизации

Актуально на: 2026-06-07

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
| `P2-LINK-07` | `codex/linked-entities-widget` | текущий HEAD (`refactor: extract linked entities widget`) | Добавлен общий секционный компонент связанных сущностей; карточка идеи переведена на него. |

## Текущая работа

- Пункт: `P2-03` — SQLite FTS5 для задач, идей, заметок и объектов.
- Ветка: `codex/linked-entities-widget`.
- Статус: блок `P2-LINK-01..07` завершён; общий компонент внедрён первым потребителем в карточке идеи.
- Проверки `P2-LINK-07`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_linked_entities_widget.py tests/test_dragdrop_policy.py tests/test_ideas_workspace.py tests/test_entity_links_read_facade.py -p no:cacheprovider` — `34 passed`.

## Следующий шаг

После ручной проверки общего списка связей идеи создать отдельную ветку от `codex/linked-entities-widget` и начать `P2-03`: сначала проверить наличие FTS5 в runtime SQLite и подготовить fallback-compatible схему/миграцию с тестами до перевода глобального поиска.
