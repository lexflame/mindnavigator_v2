# IdeasWorkspace «Идеи» — Step 1..N (Codex-ready)

## Goal
Добавить новый Workspace «Идеи» в MindNavigator: Inbox идей + инспектор + связи + материалы + трансформация в Task/Note/Object/Map Marker.

## UI Pattern
- TopBar: поиск + кнопки действий.
- Горизонтальный QSplitter:
  - **Left**: список идей (карточки).
  - **Right**: инспектор выбранной идеи (табы).

---

## Step 1. Каркас Workspace и регистрация
1) Создай модуль `mindnavigator/workspaces/ideas/`.
2) Создай `ideas_workspace.py`:
   - `class IdeasWorkspace(BaseWorkspace)`
   - методы: `_build_ui()`, `_bind_signals()`, `refresh()`, `apply_filters()`
3) Зарегистрируй Workspace в главном окне/роутере режимов:
   - новый пункт «Идеи» в левом режиме-переключателе
   - загрузка `IdeasWorkspace` по клику

**Acceptance**
- Workspace отображается и переключается без ошибок.
- Общий визуальный стиль совпадает с текущим UI.

---

## Step 2. Модель данных + контроллер/репозиторий
1) Добавь модель `Idea` с полями:
   - `id`, `project_id`, `title`, `summary`, `body_md`
   - `type` (enum: feature/story/art/research/tech/other)
   - `status` (enum: inbox/work/ripe/done/archived)
   - `value_score` (1..5), `effort_score` (1..5)
   - `created_at`, `updated_at`, `archived_at`, `source`
2) Добавь слой доступа:
   - `list(project_id=None, search=None, status=None, type=None, tags=None, archived=False)`
   - `get(id)`, `create(payload)`, `update(id, payload)`, `archive(id)`, `unarchive(id)`, `delete(id)`
3) Подключи миграцию БД (см. `DB_migration_ideas.sql`) или адаптируй под существующий миграционный механизм.

**Acceptance**
- CRUD работает.
- `list()` по умолчанию сортирует по `updated_at DESC`.

---

## Step 3. Layout: TopBar + Splitter
1) В `_build_ui()` собрать:
   - TopBar: Search (QLineEdit) + кнопки
   - QSplitter горизонтальный (Left/Right)
2) **Left**: `QListView` (предпочтительно) или `QListWidget`.
3) **Right**: `QTabWidget` с табами:
   - «Содержание», «Связи», «Материалы», «Решение»

**Acceptance**
- Пустое состояние справа (нет выбора) корректно отображается.

---

## Step 4. Список идей: модель + карточки + меню
1) Реализуй `IdeasListModel(QAbstractListModel)`.
2) Представление карточки:
   - title (fallback: «Без названия»)
   - project (если есть)
   - status
   - ⭐ value_score, ⚙ effort_score
3) Контекстное меню по правому клику:
   - Edit
   - Archive/Unarchive
   - Delete (confirm)
   - Transform → Task/Note/Object/Marker
4) Двойной клик: открыть в инспекторе.

**Acceptance**
- Меню работает, Delete всегда с confirm.

---

## Step 5. Inspector: таб «Содержание»
1) Поля:
   - `title` (QLineEdit)
   - `summary` (QLineEdit или QTextEdit)
   - `body_md` (QPlainTextEdit)
   - `type` (QComboBox)
   - `status` (QComboBox)
   - `value_score`, `effort_score` (спинбоксы 1..5 или кнопки)
2) Кнопки Save / Revert.
3) Поведение при смене выбранной идеи:
   - либо автосейв debounce, либо диалог «Сохранить изменения?»

**Acceptance**
- Сохранение обновляет запись, список отражает изменения.

---

## Step 6. Поиск и фильтры
1) Search фильтрует по `title` + `body_md`.
2) Добавь фильтры (минимум):
   - status
   - type
   - «Только архив»
3) `apply_filters()` вызывает `controller.list(...)` и обновляет модель списка.

**Acceptance**
- Фильтры комбинируются.
- На 1–5k записей UI не фризится (при необходимости: debounce поиска).

---

## Step 7. Таб «Связи»
1) Отображай связанные сущности:
   - Tasks, Notes, Objects, Map Markers, Files
2) Кнопка «Добавить связь» (можно минимально):
   - диалог выбора типа сущности и ID
3) Список кликабелен, при наличии роутинга: переход в соответствующий Workspace.

**Acceptance**
- Если связей нет, показывать пустое состояние.

---

## Step 8. Таб «Материалы»
1) Drag&Drop файлов:
   - сохранить файл через FileStorage
   - создать связь idea↔file
2) Ссылки:
   - список URL (title+url)
   - Add/Edit/Remove

**Acceptance**
- Добавление/удаление ссылок работает.
- Удаление связи файла не удаляет файл из хранилища.

---

## Step 9. Таб «Решение» (Transform)
Кнопки:
- ✅ Создать задачу
- 📝 Создать заметку
- 🧱 Создать объект
- 🗺️ Создать метку на карте

Правила трансформации:
1) Новая сущность получает:
   - `title = idea.title`
   - `body/description = idea.body_md`
   - `project_id = idea.project_id`
2) Создать обратную связь:
   - `source_idea_id` или запись в `idea_relations`
3) После трансформации:
   - `idea.status = ripe` (по умолчанию)

**Acceptance**
- Нажатие кнопки создаёт сущность и отображает её в «Связи».
- Ошибки показываются через общий механизм уведомлений/диалоги.

---

## Step 10. Горячие клавиши
- `Ctrl+Shift+N` — новая идея
- `Ctrl+Enter` — Save (в инспекторе)
- `Ctrl+1..5` — ⭐ value
- `Alt+1..5` — ⚙ effort
- `Ctrl+F` — фокус в Search

**Acceptance**
- Работают только при активном IdeasWorkspace.

---

## Step 11. Пустые состояния и QA
1) Нет идей: экран «Пока пусто» + кнопка «+ Идея».
2) Нет результатов: «Ничего не найдено».
3) Destructive действия: confirm.
4) При удалении выбранной идеи: инспектор корректно очищается.

**Acceptance**
- Нет необработанных исключений.

---

## Step 12. Таблицы связей (если нет унифицированных relations)
Если в проекте уже есть универсальная таблица связей — используй её. Иначе применяй:
- `idea_tags`
- `idea_links`
- `idea_relations`

**Acceptance**
- Каскадное удаление по `idea_id`.

---

## Definition of Done
- Workspace «Идеи» подключен и полностью работает.
- CRUD + поиск + фильтры.
- Связи/материалы.
- Transform в Task/Note/Object/Marker с обратной ссылкой.
- Стиль совпадает с проектом.
