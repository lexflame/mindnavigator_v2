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
| `P1-UI-04` | `codex/shared-editable-list` | текущий HEAD (`refactor: extract editable list component`) | Добавлен общий `EditableListWidget`, применённый в `ProjectEditDialog`. |

## Текущая работа

- Пункт: `P3-01` — генератор большой тестовой БД.
- Ветка: `codex/shared-editable-list`.
- Статус: `P1-UI-04` завершён; ветка готова к продолжению от её HEAD.
- Проверки `P1-UI-04`:
  - `python -m compileall mindnavigator main.py` — успешно;
  - `python -m pytest tests/test_projects_workspace_mn203.py tests/test_editable_list.py -p no:cacheprovider` — `21 passed`.

## Следующий шаг

Создать отдельную ветку от `codex/shared-editable-list` и выполнить `P3-01`: генератор большой тестовой БД без включения performance-порогов в обязательный CI.
