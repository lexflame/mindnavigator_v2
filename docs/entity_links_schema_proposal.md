# Proposal: единый граф связей `entity_links`

Дата: 2026-06-07
Статус: архитектурное предложение, без изменения runtime-схемы

## Цель

Ввести canonical read/write model для связей между сущностями, сохранив совместимость с
существующими таблицами и UI. Первый результат внедрения должен быть read facade "все связи
сущности", а не немедленное удаление legacy-таблиц.

Proposal покрывает:

- единый идентификатор конца связи: `entity_kind + entity_id`;
- направленные и симметричные отношения;
- связь в контексте доски или текстового упоминания;
- происхождение записи из legacy-механизма;
- идемпотентный backfill и dual-write;
- получение исходящих и входящих связей одним API.

## Текущие механизмы

| Источник | Левая сторона | Правая сторона | Дополнительная семантика |
| --- | --- | --- | --- |
| `task_attachments` | task | task/note/object/map/marker/file/image/idea | comment |
| `context_entity_links` | task/idea/note/object | task/idea/note/object | anchor text, source field |
| `idea_relations` | idea | polymorphic entity | relation kind |
| `dossier_links` | dossier | task/map/marker/note/idea/object/character | attachment-like relation |
| `character_links` | character | polymorphic entity | generic relation |
| `collection_relations` | collection item | collection item | symmetric relation kind |
| `project_related_projects` | project | project | ordered related item |
| `project_related_tasks` | project | task | ordered related item |
| `mutaboard_links` | polymorphic entity | polymorphic entity | link type scoped by board |

Отдельно существуют `mutaboard_items`, URL-таблицы, изображения, файлы и категории. Они не
являются semantic edge между двумя сущностями и не должны автоматически переноситься в
`entity_links`.

## Границы canonical graph

В `entity_links` включаются только отношения, у которых обе стороны имеют стабильную identity
в приложении.

Не включаются:

- membership: `mutaboard_items`, элементы категорий и списков;
- внешние URL: `idea_links`, repository/wiki/display properties;
- binary/file ownership: изображения объектов и идей, файлы коллекций;
- иерархия, уже являющаяся частью сущности: `tasks.parent_id`, `projects.parent_project_id`;
- project task type и другие конфигурационные ссылки.

Membership может использовать граф для навигации через отдельный read facade, но не должен
маскироваться relation kind `contains` без отдельного архитектурного решения.

## Entity Kind Registry

Registry должен быть кодовым модулем, а не жестким SQL `CHECK`, чтобы новый тип можно было
добавить без rebuild общей таблицы.

Начальный набор:

- `task`;
- `project`;
- `map`;
- `marker`;
- `note`;
- `idea`;
- `object`;
- `character`;
- `dossier`;
- `collection_item`;
- `file`;
- `concept_board`;
- `concept_version`;
- `concept_solution`.

Generic `image` не входит в начальный registry: `idea_images` и `object_images` имеют независимые
пространства integer ID. Для них потребуются отдельные kinds (`idea_image`, `object_image`) либо
глобальная media identity.

Для каждого kind registry определяет:

- storage table и проверку существования;
- display resolver;
- navigation action;
- допустимость удаления dangling links;
- aliases legacy-названий, например `mutaboard -> concept_board`.

`entity_id` всегда положительный integer внутри kind. Глобальный UUID сейчас не требуется и
может быть добавлен позднее как отдельный identity layer.

## Relation Kind Registry

Каждый relation kind задает:

- canonical name;
- `directed` или `symmetric`;
- допустимые source/target kinds;
- inverse label для UI;
- возможность нескольких связей между той же парой через qualifier;
- правила удаления и отображения.

Начальный словарь:

| Canonical kind | Направление | Назначение |
| --- | --- | --- |
| `related` | symmetric | общая смысловая связь |
| `references` | directed | источник ссылается на цель |
| `attached` | directed | вложение/рабочий материал сущности |
| `mentions` | directed | текстовое упоминание с evidence |
| `inspires` | directed | источник вдохновляет цель |
| `develops` | directed | источник развивает цель |
| `transforms_to` | directed | преобразование в цель |
| `contradicts` | symmetric | смысловое противоречие |
| `project_related` | symmetric | связь проектов |
| `project_task` | directed | задача, связанная с проектом вне ownership |
| `collection_relation` | symmetric | типизированная связь элементов коллекции |

Legacy relation values сохраняются в `legacy_relation_kind` внутри metadata до утверждения
полного canonical словаря.

## Предлагаемая схема

```sql
CREATE TABLE entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_kind TEXT NOT NULL,
    source_id INTEGER NOT NULL CHECK (source_id > 0),
    target_kind TEXT NOT NULL,
    target_id INTEGER NOT NULL CHECK (target_id > 0),
    relation_kind TEXT NOT NULL,
    scope_kind TEXT NOT NULL DEFAULT '',
    scope_id INTEGER NOT NULL DEFAULT 0 CHECK (scope_id >= 0),
    qualifier TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    origin TEXT NOT NULL DEFAULT 'native',
    origin_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (source_kind <> target_kind OR source_id <> target_id),
    UNIQUE (
        source_kind,
        source_id,
        target_kind,
        target_id,
        relation_kind,
        scope_kind,
        scope_id,
        qualifier
    )
);

CREATE INDEX idx_entity_links_source
    ON entity_links(source_kind, source_id, relation_kind, id);

CREATE INDEX idx_entity_links_target
    ON entity_links(target_kind, target_id, relation_kind, id);

CREATE INDEX idx_entity_links_scope
    ON entity_links(scope_kind, scope_id, relation_kind, id);

CREATE UNIQUE INDEX idx_entity_links_origin
    ON entity_links(origin, origin_id)
    WHERE origin <> 'native' AND origin_id IS NOT NULL;
```

### Назначение полей

- `scope_kind/scope_id`: необязательный контейнер отношения. Для `mutaboard_links` это
  `concept_board + mutaboard_id`; отсутствие scope кодируется `'' + 0` для надежного UNIQUE.
- `qualifier`: стабильная часть identity нескольких edges одной пары. Для text mention это
  нормализованные `source_field + anchor_text`; для обычной связи пустая строка.
- `metadata_json`: comment, anchor text, source field, sort order и legacy relation value.
- `origin/origin_id`: обратная трассировка и идемпотентный backfill, например
  `task_attachments + 42`.

JSON не должен использоваться для полей, по которым выполняется основной поиск или
уникальность. Metadata является расширением, а не заменой колонок.

## Направление и canonical ordering

Для directed relation source и target сохраняются в пользовательском направлении.

Для symmetric relation storage facade обязан упорядочить концы по tuple
`(entity_kind, entity_id)` до insert. Поэтому связь A-B и B-A получает одну запись. UI может
показывать ее с любой стороны, не создавая обратный дубль.

`context_entity_links` остаются directed, даже если одновременно создают generic relation:
направление хранит место текстового упоминания.

## Проверка ссылочной целостности

SQLite не поддерживает polymorphic foreign key. Поэтому целостность обеспечивается тремя
уровнями:

1. `EntityKindRegistry` проверяет существование обоих endpoints перед записью.
2. Все удаления сущностей вызывают `delete_links_for_entity(kind, id)` в той же транзакции.
3. Периодический validator выявляет dangling endpoints и возвращает отчет без молчаливого
   удаления.

Миграционные и integrity-тесты должны запускать validator вместе с `PRAGMA foreign_key_check`.

## Mapping legacy-таблиц

| Legacy source | Canonical mapping |
| --- | --- |
| `task_attachments` | `task -> kind/ref_id`, обычно `attached`; comment в metadata |
| `context_entity_links` | source -> target, `mentions`; anchor/source field в metadata и qualifier |
| `idea_relations` | `idea -> entity`, relation kind через registry/alias |
| `dossier_links` | `dossier -> entity`, `attached` |
| `character_links` | `character -> entity`, `related` |
| `collection_relations` | symmetric `collection_relation`; исходный kind в metadata |
| `project_related_projects` | symmetric `project_related`; sort order в metadata |
| `project_related_tasks` | `project -> task`, `project_task`; sort order в metadata |
| `mutaboard_links` | source -> target с исходным link type и scope concept board |

`task_attachments(kind='file')` могут быть перенесены после подтверждения, что `ref_id` всегда
указывает на `cloud_files`. Строки `kind='image'` остаются legacy до устранения неоднозначности
image identity.

## Storage API

Минимальный facade:

```python
add_entity_link(source, target, relation_kind, *, scope=None, qualifier="", metadata=None)
fetch_entity_links(entity, *, direction="both", relation_kinds=None, scope=None)
delete_entity_link(link_id)
delete_links_for_entity(entity)
validate_entity_links()
```

`fetch_entity_links(..., direction="both")` возвращает нормализованную модель с полями:

- `link_id`;
- `entity` и `other_entity` относительно запрошенной стороны;
- `direction`: `outgoing`, `incoming` или `symmetric`;
- canonical и display relation labels;
- scope, metadata и origin.

UI не должен самостоятельно объединять результаты нескольких legacy fetch-методов.

## План внедрения

### Этап 1. Registry и read facade

1. Добавить `EntityRef`, entity kind registry и relation kind registry.
2. Реализовать facade, который читает legacy-таблицы и возвращает единую модель без новой
   таблицы.
3. Добавить parity-тесты на task, idea, dossier, collection и concept board.

Rollback: удалить facade; persistent data не меняются.

### Этап 2. Shadow table и backfill

1. Создать `entity_links` миграцией.
2. Выполнить idempotent backfill с `origin/origin_id`.
3. Сравнить количество и содержимое edges с legacy facade.
4. Не переключать UI на новую таблицу до прохождения parity.

Rollback: чтение остается legacy; shadow table можно игнорировать, не удаляя данные.

### Этап 3. Dual-write

1. Новые link operations пишут legacy и canonical table в одной savepoint-транзакции.
2. Reads продолжают использовать legacy facade с фоновым parity assertion в тестах.
3. Исправить расхождения до cutover.

Rollback: отключить canonical write feature flag; legacy остается authoritative.

### Этап 4. Read cutover

1. Перевести unified linked-entities panel на canonical reads.
2. Сохранить legacy adapters для старых экранов.
3. Добавить incoming links и scope filters.

Rollback: вернуть read feature flag на legacy facade.

### Этап 5. Canonical ownership

Только после минимум одного стабильного релиза canonical table становится authoritative.
Legacy-таблицы сначала переводятся в compatibility view/adapters. Физическое удаление требует
отдельного решения, backup и migration tests на реальные старые БД.

## Критерии приемки

- Одна сущность получает исходящие и входящие links одним вызовом.
- Symmetric links не дублируются при обратном insert.
- Directed links сохраняют направление и inverse label.
- Backfill повторяем и не создает дубли.
- Для каждой canonical строки известен legacy origin либо `native`.
- Unknown kind/relation отклоняется registry с понятной ошибкой.
- Dangling link обнаруживается validator.
- Dual-write полностью откатывается при ошибке любой стороны.
- Parity-тесты подтверждают task/context/idea/dossier/character/collection/project/concept-board.
- Существующие UI и экспорт не меняются до отдельного cutover-этапа.

## Риски

- Одинаковая пара сущностей может иметь несколько разных смыслов; нельзя дедуплицировать только
  по endpoints.
- Text mentions требуют qualifier, иначе разные упоминания сольются.
- Legacy relation kinds не полностью унифицированы и нуждаются в aliases.
- Polymorphic endpoints требуют application-level integrity и строгих delete paths.
- Одновременный перенос membership, attachments и semantic links сделает API неоднозначным;
  эти классы должны мигрировать независимо.
- Удаление legacy-таблиц до стабильного dual-read/dual-write периода создает неприемлемый риск
  потери пользовательских связей.
