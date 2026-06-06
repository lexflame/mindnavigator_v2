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
| `P3-02` (этап 2) | `codex/tasks-model-reload-benchmark` | текущий HEAD (`test: benchmark tasks model reload`) | Runner расширен измерением `TasksModel.refresh()` в offscreen Qt. |

## Текущая работа

- Пункт: `P3-02` — измерение ключевых операций на больших БД, этап 3.
- Ветка: `codex/tasks-model-reload-benchmark`.
- Статус: этап 2 завершён; остаются сценарии открытия форм.
- Проверки этапа 2:
  - `python -m compileall mindnavigator main.py scripts/run_perf_benchmarks.py` — успешно;
  - `python -m pytest tests/test_run_perf_benchmarks.py tests/test_tasks_workspace_mn202.py -k "run_perf_benchmarks" -p no:cacheprovider` — `2 passed`, `94 deselected`;
  - локальный профиль 5k, 3 итерации: `fetch_tasks` p50 `163.787 ms`, `global_search` p50 `169.212 ms`, `tasks_model_reload` p50 `292.200 ms`.

## Следующий шаг

Создать отдельную ветку от `codex/tasks-model-reload-benchmark` и завершить `P3-02`: определить и добавить стабильные сценарии конструирования формы задачи и формы проекта без показа modal event loop.
