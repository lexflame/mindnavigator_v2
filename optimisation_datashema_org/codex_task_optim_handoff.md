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
| `P2-02` | `codex/global-search-service` | текущий HEAD (`refactor: extract global search service`) | Сбор результатов глобального поиска перенесён из `SearchNav` в независимый от Qt service. |

## Текущая работа

- Пункт: `P3-02` — измерение ключевых операций на больших БД.
- Ветка: `codex/global-search-service`.
- Статус: `P2-02` завершён; ветка готова к продолжению от её HEAD.
- Проверки `P2-02`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_global_search_service.py tests/test_search_nav_debounce.py tests/test_theme_switch_runtime.py -k "global_search or search_nav" -p no:cacheprovider` — `5 passed`, `4 deselected`.

## Следующий шаг

Создать отдельную ветку от `codex/global-search-service` и выполнить `P3-02`: добавить необязательный benchmark runner для `fetch_tasks` и глобального поиска на БД 5k/20k с выводом p50/p95 без обязательных CI-порогов.
