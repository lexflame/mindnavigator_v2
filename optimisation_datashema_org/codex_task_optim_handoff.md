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
| `P2-LINK-02` | `codex/entity-links-read-facade` | текущий HEAD (`feat: add entity links read facade`) | Добавлены `EntityRef`, `EntityLinkView` и единый read API поверх пяти legacy relation tables. |

## Текущая работа

- Пункт: `P2-LINK-03` — расширение общего API связей и перевод потребителей.
- Ветка: `codex/entity-links-read-facade`.
- Статус: `P2-LINK-02` завершён без persistent schema changes.
- Проверки `P2-LINK-02`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_entity_links_read_facade.py tests/test_context_entity_linking.py tests/test_dossier_storage.py tests/test_idea_storage_search.py -p no:cacheprovider` — `14 passed`.

## Следующий шаг

Создать отдельную ветку от `codex/entity-links-read-facade` и продолжить `P2-LINK-03`: добавить в facade `character_links`, project relations и concept-board links, затем определить первый UI-потребитель общего API.
