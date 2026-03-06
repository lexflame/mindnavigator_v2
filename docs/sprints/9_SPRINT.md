# Sprint 9: Modern Modes, Redesign, and Workspace Expansion

## Sprint Status
- Planned: 2026-03-06
- Status: In Progress
- Source root: `MN-195`
- Source project: `MindNavigator / CODEX` (`project_id=24`)
- Source DB: `\\gtx\YandexDisk\.mindnavigator\mindnavigator.db`

## Sprint Goal
Deliver a staged redesign and feature expansion from `MN-195` with conflict-safe execution order, explicit validation, and rollback notes.

## Root Task
- `MN-195` `# SPRINT :: Модерн спринт - Новые режимы - Редизайн`
- Priority: `High`
- Schedule: `2026-03-06 11:00`

### Root Description Directives
- ## Постановщик задач MindNavigator
- ## Режим работы по спринту: автоматический переход от задачи к задаче
- ## Рефактор и активное дополнение PARITY
- ## Комментирование всех классов при работе с кодом на менер PHPDoc
- ## Комментирование всех функции при работе с кодом на менер PHPDoc
- ## Комментирование всех ключевых узлов функций и классов на менер PHPDoc
- ## Если необходимо получить разрешения от пользователя на операции требующего его внимания отправлять сообщение в телеграмм
- ## В ключевых этапах работы над кодом отправлять сообщение в телеграмм
- ## В конце спринта выполнить добавленные задачи в PARITY
- ## Реализовать в рамках спринта класс мини-интелектуального анализа для описания, задач и строк (сформировать внутри спринта отдельный PARTITION)
- ## В рамках спринта провести ревизию на предмет неиспользуемых участков кода (сформировать внутри спринта отдельный PARTITION)

## Source Tree Summary
- Total nodes including root: `70`
- Partitions under root: `14`
- Leaf and nested tasks: `55`

### Partitions
- `MN-196` `## PARTITION :: Design :: Проработка режима `Задачи`` (children: `8`)
- `MN-201` `## PARTITION :: Design :: Проработка режима `Проекты`` (children: `3`)
- `MN-202` `## PARTITION :: Feat :: Фичи для режима `Задачи`` (children: `11`)
- `MN-203` `## PARTITION :: Feat :: Фичи для режима `Проекты`` (children: `1`)
- `MN-204` `## PARTITION :: Feat :: Worksapce`s :: Новый режим "Персонажи"` (children: `3`)
- `MN-205` `## PARTITION :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw"` (children: `4`)
- `MN-206` `## PARTITION :: Feat :: Фичи для режима `Файлы`` (children: `3`)
- `MN-207` `## PARTITION :: Feat :: Фичи для режима `Коллекции`` (children: `3`)
- `MN-208` `## PARTITION :: Feat :: Фичи для режима `Идеи`` (children: `1`)
- `MN-209` `## PARTITION :: Feat :: Rafector Workspace :: Самостоятельная проработка CODEX-ом режима "Карты"` (children: `0`)
- `MN-210` `## PARTITION :: Design :: Проработка "Настройки"` (children: `3`)
- `MN-264` `## PARTITION :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX и любыми другими ИИ.` (children: `3`)
- `MN-268` `## PARTITION :: Feat :: View` (children: `8`)
- `MN-289` `## PARTITION :: PARSE_DATA :: Импортировать в "Покупки" следующий список товаров со всеми свойствами` (children: `0`)

## Execution Waves
### 1. Wave 1 - Foundation, API, and Critical Fixes
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-264` ## PARTITION :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX и любыми другими ИИ.
- `MN-265` TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - сформировать для этого отдельный PATITION
- `MN-267` TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - Релизовать для всех сущностей приложения - создание, редактирование, чтение, удаление
- `MN-266` TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - API должен дать ИИ описание всех своих интерфейсов для самообучения ИИ работы с ним
- `MN-253` FIX :: Список задач :: Отладить и исправить прикрепление идей и заметок в задаче
- `MN-274` FIX :: Идеи :: Сделать цвет элементов списка связей внутри формы Идеи белым цветом
- `MN-283` FIX :: Feat :: Настройки :: Блок настроек резервного копирования весь "склеился", элементы блока наезжают друг на друга

### 2. Wave 2 - Tasks Remaster Baseline
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-196` ## PARTITION :: Design :: Проработка режима `Задачи`
- `MN-197` TASK :: Remaster :: Список задач :: Символ `+`  для кнопки добавления подзадачи заменить на иконки qtawesome и отцентровать по центру кнопки
- `MN-198` TASK :: Remaster :: Список задач :: Кнопка добавления подзадачи должна занимать всю высоту строки задачи и не иметь верхней и нижней границы
- `MN-275` TASK :: Remaster :: Список задач :: Кнопка "Добавить задачу"  не должна иметь скруглений, верхней и нижней границы.
- `MN-200` TASK :: Remaster :: Список задач :: Кнопка "Добавить задачу" для дня должна занимать всю высоту строки разделителя
- `MN-238` TASK :: Remaster :: Список задач :: `Shift`+LeftClick mouse - расскрывает все древо вложенных задач, т.е. расскрывает все вложенные дочериние задачи.
- `MN-239` TASK :: Remaster :: Задачи :: Список задач :: По-умолчанию чек-бокс "Время" в форме быстрого создания задачи выбран
- `MN-240` TASK :: Remaster :: Задачи :: Список задач :: По-умолчанию время +1 час к текущему времени, если не выбранно иное, в форме быстрого создания задачи

### 3. Wave 3 - Global View Primitives
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-268` ## PARTITION :: Feat :: View
- `MN-269` TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` везде квадратным
- `MN-270` TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` всегда заполняет всю высоты блока строчки
- `MN-271` TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` для областей проекта сдвинуть до конца влево
- `MN-273` TASK :: Feat :: View :: Список задач :: Чек-бокс выполнения задачи сделать равным размеру `Блок с тремя точками`
- `MN-272` TASK :: Feat :: View :: Список проектов :: Стрелочки раскрытия проектов сделать по аналогии с раскрытием списка подзадач в режиме "Список задач"

### 4. Wave 4 - Tasks Feature Layer
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-202` ## PARTITION :: Feat :: Фичи для режима `Задачи`
- `MN-237` TASK :: Feat :: Задачи :: Список задач :: При работе с диалоговыми окнами просмотра и редактирования задач реализовать оверлей
- `MN-251` TASK :: Feat :: Список задач :: Применить эффект красивого появления диалоговых окон
- `MN-236` TASK :: Feat :: Задачи :: Список задач :: Реализовать сворачивание диалоговых окон просмотра и редактирования задач
- `MN-241` TASK :: Feat :: Задачи :: Список задач :: Новые внешний вид свойства "Приоритет" (`Переключатель приоритета`)
- `MN-242` TASK :: Feat :: Задачи :: Список задач :: Векторные фоновые оверлэй поверх цветового маркера для значения свойства задачи "Тема маркера"
- `MN-250` ADDON :: Feat :: Оверлей фоновые изображения :: Задачи :: Векторные фоновые оверлэй - внешний вид
- `MN-243` TASK :: Задачи :: Список задач :: Кнопку Режим "Gantt" перенести в верхний блок, разместить слева от кнопок "Экспорт"/"Импорт" с вырваниеванием к левому краю
- `MN-247` TASK :: Feat :: Задачи :: Список задач :: Подписи для кнопок: "Gantt", "Board", "Dash"
- `MN-244` TASK :: Feat :: Задачи :: Список задач :: Справа от режима "Gantt" добавить кнопки "Board" и "Dash"
- `MN-245` ADDON :: Feat :: Режим "Board" :: Задачи :: Список задач :: Режим "Board"
- `MN-246` ADDON :: Feat :: Режим "Board" :: Задачи :: Список задач :: Режим "Dash"
- `MN-249` TASK :: Feat :: Задачи :: Список задач :: По правому клику машки расскрывать выпадающее меню с переходам в вложениям
- `MN-252` TASK :: Feat :: Список задач :: Интелектуальный подбор проекта по заголовку задачи
- `MN-248` TASK :: Feat :: Задачи :: Список задач :: Между "Переключателем даты" и фильтром "Приоритета" разместить 4-5 ссылкок на проекты

### 5. Wave 5 - Projects
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-201` ## PARTITION :: Design :: Проработка режима `Проекты`
- `MN-254` TASK :: Feat :: Проекты :: Список проектов :: `Переключатель приоритета` аналогичные `Переключателю приоритета` в списке задач
- `MN-255` TASK :: Feat :: Проекты :: Список проектов :: Цветовые бейджы вложений при наведении на проект по центру строки проекта
- `MN-203` ## PARTITION :: Feat :: Фичи для режима `Проекты`
- `MN-235` TASK :: Feat :: Проекты :: Список проектов :: Реализовать свойство для проектов "Каталог репозитория"
- `MN-256` TASK :: Feat :: Проекты :: Список проектов :: Справа от кнопки "Импорт" в панели быстрого доступа реализовать кнопку "GRAPH"

### 6. Wave 6 - Files and Collections
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-206` ## PARTITION :: Feat :: Фичи для режима `Файлы`
- `MN-279` TASK :: Feat :: Файлы :: Правила хранения индекса поиска по файлам
- `MN-276` TASK :: Feat :: Файлы :: Под блоком кнопок Синхронизации/Переиндексации добавить блок умного поиска с подсказками
- `MN-277` TASK :: Feat :: Файлы :: Режим поиска по файлам переключает всю рабочую область файлов в режим больших "Эскизов"
- `MN-278` ADDON :: Feat :: Файлы :: Режим "Эскизов" - среднее между главной страницей в "Pinterest" и видом "Огромные значки" и "Область просмотра" как в Проводнике
- `MN-207` ## PARTITION :: Feat :: Фичи для режима `Коллекции`
- `MN-281` TASK :: Feat :: Коллекции :: При формирования коллекции исключать из нее файлы "Thumbs.db"
- `MN-280` TASK :: Feat :: Коллекции :: Реализовать возможность удалять отдельные элементы коллекции (файлы при этом не удалять)
- `MN-282` TASK :: Remaster :: Коллекции :: Цвет текста в описании коллекции сделать белым цветом

### 7. Wave 7 - New Workspaces and Maps
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-204` ## PARTITION :: Feat :: Worksapce`s :: Новый режим "Персонажи"
- `MN-257` TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - сфорировать отдельный PARTITION для реализации данного режима
- `MN-258` TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - CODEX самостоятельно расисывает данный режим и прорабатывает его особенности
- `MN-259` TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - Персонажей можно прикрепить к любой сущности приложения
- `MN-205` ## PARTITION :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw"
- `MN-260` TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - сфорировать отдельный PARTITION для реализации данного режима
- `MN-263` TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - Прототип режима Mindomo
- `MN-261` TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - CODEX самостоятельно расисывает данный режим и прорабатывает его особенности
- `MN-262` TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - Элементы можно подвязывать из любых режимов приложения
- `MN-209` ## PARTITION :: Feat :: Rafector Workspace :: Самостоятельная проработка CODEX-ом режима "Карты"

### 8. Wave 8 - Settings and Final View Polish
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-210` ## PARTITION :: Design :: Проработка "Настройки"
- `MN-285` TASK :: Feat :: Настройки :: Сверху над кнопкой перехода в режим "Настройки" релизовать "переключатель" светлая/тёмная тема - Toggle-Switch
- `MN-284` TASK :: Feat :: Настройки :: Переключать весь интерфейс приложения при переключении языка, запрашивать перезапуск программы
- `MN-286` TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Объекты" сделать по подобию навигации "Список задач" - превью в каждой строчке
- `MN-287` TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Заметки" сделать по подобию навигации "Список задач" - превью в каждой строчке
- `MN-288` TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Идеи" сделать по подобию навигации "Список задач" - превью в каждой строчке

### 9. Wave 9 - Purchases Parse Data and Closure
- Objective: isolate a coherent change surface and reduce merge conflicts.
- Task IDs:
- `MN-289` ## PARTITION :: PARSE_DATA :: Импортировать в "Покупки" следующий список товаров со всеми свойствами
- `MN-208` ## PARTITION :: Feat :: Фичи для режима `Идеи`

## Task Decomposition Matrix
| Task | Type | Wave | Scope from title and description | Dependencies | Validation | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| `MN-196` | partition | 2 | ## PARTITION :: Design :: Проработка режима `Задачи`; ### Внутри задачи для feat, fix, design | Wave 1 outputs | compileall; focused pytest by module | Revert MN-196 patch and keep previous behavior |
| `MN-197` | task | 2 | TASK :: Remaster :: Список задач :: Символ `+`  для кнопки добавления подзадачи заменить на иконки qtawesome и отцентровать по центру кнопки | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-197 patch and keep previous behavior |
| `MN-198` | task | 2 | TASK :: Remaster :: Список задач :: Кнопка добавления подзадачи должна занимать всю высоту строки задачи и не иметь верхней и нижней границы | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-198 patch and keep previous behavior |
| `MN-200` | task | 2 | TASK :: Remaster :: Список задач :: Кнопка "Добавить задачу" для дня должна занимать всю высоту строки разделителя | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-200 patch and keep previous behavior |
| `MN-201` | partition | 5 | ## PARTITION :: Design :: Проработка режима `Проекты` | Wave 4 outputs | compileall; focused pytest by module | Revert MN-201 patch and keep previous behavior |
| `MN-202` | partition | 4 | ## PARTITION :: Feat :: Фичи для режима `Задачи` | Wave 3 outputs | compileall; focused pytest by module | Revert MN-202 patch and keep previous behavior |
| `MN-203` | partition | 5 | ## PARTITION :: Feat :: Фичи для режима `Проекты` | Wave 4 outputs | compileall; focused pytest by module | Revert MN-203 patch and keep previous behavior |
| `MN-204` | partition | 7 | ## PARTITION :: Feat :: Worksapce`s :: Новый режим "Персонажи" | Wave 6 outputs | compileall; focused pytest by module | Revert MN-204 patch and keep previous behavior |
| `MN-205` | partition | 7 | ## PARTITION :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" | Wave 6 outputs | compileall; focused pytest by module | Revert MN-205 patch and keep previous behavior |
| `MN-206` | partition | 6 | ## PARTITION :: Feat :: Фичи для режима `Файлы` | Wave 5 outputs | compileall; focused pytest by module | Revert MN-206 patch and keep previous behavior |
| `MN-207` | partition | 6 | ## PARTITION :: Feat :: Фичи для режима `Коллекции` | Wave 5 outputs | compileall; focused pytest by module | Revert MN-207 patch and keep previous behavior |
| `MN-208` | partition | 9 | ## PARTITION :: Feat :: Фичи для режима `Идеи` | Wave 8 outputs | compileall; focused pytest by module | Revert MN-208 patch and keep previous behavior |
| `MN-209` | partition | 7 | ## PARTITION :: Feat :: Rafector Workspace :: Самостоятельная проработка CODEX-ом режима "Карты" | Wave 6 outputs | compileall; pytest tests -k workspace | Revert MN-209 patch and keep previous behavior |
| `MN-210` | partition | 8 | ## PARTITION :: Design :: Проработка "Настройки" | Wave 7 outputs | compileall; focused pytest by module | Revert MN-210 patch and keep previous behavior |
| `MN-235` | task | 5 | TASK :: Feat :: Проекты :: Список проектов :: Реализовать свойство для проектов "Каталог репозитория"; ## В рамках данной задачи реализовать класс для простого опроса репоизитория и получения текущего состояния локальной ветки и ее имени | Wave 4 outputs | compileall; pytest tests -k tasks | Revert MN-235 patch and keep previous behavior |
| `MN-236` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Реализовать сворачивание диалоговых окон просмотра и редактирования задач; ## При клике по области оверлея интерфейса вне диалогового окна сворачивать диалоговое окно | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-236 patch and keep previous behavior |
| `MN-237` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: При работе с диалоговыми окнами просмотра и редактирования задач реализовать оверлей | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-237 patch and keep previous behavior |
| `MN-238` | task | 2 | TASK :: Remaster :: Список задач :: `Shift`+LeftClick mouse - расскрывает все древо вложенных задач, т.е. расскрывает все вложенные дочериние задачи. | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-238 patch and keep previous behavior |
| `MN-239` | task | 2 | TASK :: Remaster :: Задачи :: Список задач :: По-умолчанию чек-бокс "Время" в форме быстрого создания задачи выбран | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-239 patch and keep previous behavior |
| `MN-240` | task | 2 | TASK :: Remaster :: Задачи :: Список задач :: По-умолчанию время +1 час к текущему времени, если не выбранно иное, в форме быстрого создания задачи | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-240 patch and keep previous behavior |
| `MN-241` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Новые внешний вид свойства "Приоритет" (`Переключатель приоритета`); ## Два состояния hover/unhover | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-241 patch and keep previous behavior |
| `MN-242` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Векторные фоновые оверлэй поверх цветового маркера для значения свойства задачи "Тема маркера" | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-242 patch and keep previous behavior |
| `MN-243` | task | 4 | TASK :: Задачи :: Список задач :: Кнопку Режим "Gantt" перенести в верхний блок, разместить слева от кнопок "Экспорт"/"Импорт" с вырваниеванием к левому краю | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-243 patch and keep previous behavior |
| `MN-244` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Справа от режима "Gantt" добавить кнопки "Board" и "Dash"; ## Режим "Board" - "Кан-Бан" реализовать с приминением внешнего вида приложения | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-244 patch and keep previous behavior |
| `MN-245` | addon | 4 | ADDON :: Feat :: Режим "Board" :: Задачи :: Список задач :: Режим "Board"; ## Реализовать с приминением внешнего вида приложения | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-245 patch and keep previous behavior |
| `MN-246` | addon | 4 | ADDON :: Feat :: Режим "Board" :: Задачи :: Список задач :: Режим "Dash"; ## Реализовать с приминением внешнего вида приложения | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-246 patch and keep previous behavior |
| `MN-247` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Подписи для кнопок: "Gantt", "Board", "Dash"; ## GANTT | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-247 patch and keep previous behavior |
| `MN-248` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: Между "Переключателем даты" и фильтром "Приоритета" разместить 4-5 ссылкок на проекты; ## Проекты с самым большим количеством задач | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-248 patch and keep previous behavior |
| `MN-249` | task | 4 | TASK :: Feat :: Задачи :: Список задач :: По правому клику машки расскрывать выпадающее меню с переходам в вложениям | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-249 patch and keep previous behavior |
| `MN-250` | addon | 4 | ADDON :: Feat :: Оверлей фоновые изображения :: Задачи :: Векторные фоновые оверлэй - внешний вид; ## Каталог с источником изображений: `assets\badge\` | Wave 3 outputs | compileall; focused pytest by module | Revert MN-250 patch and keep previous behavior |
| `MN-251` | task | 4 | TASK :: Feat :: Список задач :: Применить эффект красивого появления диалоговых окон | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-251 patch and keep previous behavior |
| `MN-252` | task | 4 | TASK :: Feat :: Список задач :: Интелектуальный подбор проекта по заголовку задачи | Wave 3 outputs | compileall; pytest tests -k tasks | Revert MN-252 patch and keep previous behavior |
| `MN-253` | fix | 1 | FIX :: Список задач :: Отладить и исправить прикрепление идей и заметок в задаче | None | compileall; focused pytest by module | Revert MN-253 patch and keep previous behavior |
| `MN-254` | task | 5 | TASK :: Feat :: Проекты :: Список проектов :: `Переключатель приоритета` аналогичные `Переключателю приоритета` в списке задач | Wave 4 outputs | compileall; pytest tests -k tasks | Revert MN-254 patch and keep previous behavior |
| `MN-255` | task | 5 | TASK :: Feat :: Проекты :: Список проектов :: Цветовые бейджы вложений при наведении на проект по центру строки проекта; ## Собирать суммарно из всех задач проекта | Wave 4 outputs | compileall; pytest tests -k tasks | Revert MN-255 patch and keep previous behavior |
| `MN-256` | task | 5 | TASK :: Feat :: Проекты :: Список проектов :: Справа от кнопки "Импорт" в панели быстрого доступа реализовать кнопку "GRAPH"; ## Сфорировать отдельный PARTITION для данного режима | Wave 4 outputs | compileall; pytest tests -k tasks | Revert MN-256 patch and keep previous behavior |
| `MN-257` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - сфорировать отдельный PARTITION для реализации данного режима | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-257 patch and keep previous behavior |
| `MN-258` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - CODEX самостоятельно расисывает данный режим и прорабатывает его особенности | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-258 patch and keep previous behavior |
| `MN-259` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим "Персонажи" - Персонажей можно прикрепить к любой сущности приложения | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-259 patch and keep previous behavior |
| `MN-260` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - сфорировать отдельный PARTITION для реализации данного режима | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-260 patch and keep previous behavior |
| `MN-261` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - CODEX самостоятельно расисывает данный режим и прорабатывает его особенности | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-261 patch and keep previous behavior |
| `MN-262` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - Элементы можно подвязывать из любых режимов приложения | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-262 patch and keep previous behavior |
| `MN-263` | task | 7 | TASK :: Feat :: Worksapce`s :: Новый режим, рабочее название "MindDraw" - Прототип режима Mindomo | Wave 6 outputs | compileall; pytest tests -k tasks | Revert MN-263 patch and keep previous behavior |
| `MN-264` | partition | 1 | ## PARTITION :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX и любыми другими ИИ. | None | compileall; pytest tests -k entity_api | Revert MN-264 patch and keep previous behavior |
| `MN-265` | task | 1 | TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - сформировать для этого отдельный PATITION | None | compileall; pytest tests -k tasks | Revert MN-265 patch and keep previous behavior |
| `MN-266` | task | 1 | TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - API должен дать ИИ описание всех своих интерфейсов для самообучения ИИ работы с ним | None | compileall; pytest tests -k tasks | Revert MN-266 patch and keep previous behavior |
| `MN-267` | task | 1 | TASK :: Feat :: Worksapce`s :: Реализовать API для интеграции с CODEX - Релизовать для всех сущностей приложения - создание, редактирование, чтение, удаление | None | compileall; pytest tests -k tasks | Revert MN-267 patch and keep previous behavior |
| `MN-268` | partition | 3 | ## PARTITION :: Feat :: View | Wave 2 outputs | compileall; pytest tests -k workspace | Revert MN-268 patch and keep previous behavior |
| `MN-269` | task | 3 | TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` везде квадратным | Wave 2 outputs | compileall; pytest tests -k tasks | Revert MN-269 patch and keep previous behavior |
| `MN-270` | task | 3 | TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` всегда заполняет всю высоты блока строчки | Wave 2 outputs | compileall; pytest tests -k tasks | Revert MN-270 patch and keep previous behavior |
| `MN-271` | task | 3 | TASK :: Feat :: View :: Глобально во всех Workspace :: `Блок с тремя точками` для областей проекта сдвинуть до конца влево | Wave 2 outputs | compileall; pytest tests -k tasks | Revert MN-271 patch and keep previous behavior |
| `MN-272` | task | 3 | TASK :: Feat :: View :: Список проектов :: Стрелочки раскрытия проектов сделать по аналогии с раскрытием списка подзадач в режиме "Список задач" | Wave 2 outputs | compileall; pytest tests -k tasks | Revert MN-272 patch and keep previous behavior |
| `MN-273` | task | 3 | TASK :: Feat :: View :: Список задач :: Чек-бокс выполнения задачи сделать равным размеру `Блок с тремя точками` | Wave 2 outputs | compileall; pytest tests -k tasks | Revert MN-273 patch and keep previous behavior |
| `MN-274` | fix | 1 | FIX :: Идеи :: Сделать цвет элементов списка связей внутри формы Идеи белым цветом | None | compileall; focused pytest by module | Revert MN-274 patch and keep previous behavior |
| `MN-275` | task | 2 | TASK :: Remaster :: Список задач :: Кнопка "Добавить задачу"  не должна иметь скруглений, верхней и нижней границы. | Wave 1 outputs | compileall; pytest tests -k tasks | Revert MN-275 patch and keep previous behavior |
| `MN-276` | task | 6 | TASK :: Feat :: Файлы :: Под блоком кнопок Синхронизации/Переиндексации добавить блок умного поиска с подсказками | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-276 patch and keep previous behavior |
| `MN-277` | task | 6 | TASK :: Feat :: Файлы :: Режим поиска по файлам переключает всю рабочую область файлов в режим больших "Эскизов" | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-277 patch and keep previous behavior |
| `MN-278` | addon | 6 | ADDON :: Feat :: Файлы :: Режим "Эскизов" - среднее между главной страницей в "Pinterest" и видом "Огромные значки" и "Область просмотра" как в Проводнике | Wave 5 outputs | compileall; focused pytest by module | Revert MN-278 patch and keep previous behavior |
| `MN-279` | task | 6 | TASK :: Feat :: Файлы :: Правила хранения индекса поиска по файлам; Хранить отдельным индексом - путь - распрасить по `\` | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-279 patch and keep previous behavior |
| `MN-280` | task | 6 | TASK :: Feat :: Коллекции :: Реализовать возможность удалять отдельные элементы коллекции (файлы при этом не удалять) | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-280 patch and keep previous behavior |
| `MN-281` | task | 6 | TASK :: Feat :: Коллекции :: При формирования коллекции исключать из нее файлы "Thumbs.db" | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-281 patch and keep previous behavior |
| `MN-282` | task | 6 | TASK :: Remaster :: Коллекции :: Цвет текста в описании коллекции сделать белым цветом | Wave 5 outputs | compileall; pytest tests -k tasks | Revert MN-282 patch and keep previous behavior |
| `MN-283` | fix | 1 | FIX :: Feat :: Настройки :: Блок настроек резервного копирования весь "склеился", элементы блока наезжают друг на друга | None | compileall; focused pytest by module | Revert MN-283 patch and keep previous behavior |
| `MN-284` | task | 8 | TASK :: Feat :: Настройки :: Переключать весь интерфейс приложения при переключении языка, запрашивать перезапуск программы | Wave 7 outputs | compileall; pytest tests -k tasks | Revert MN-284 patch and keep previous behavior |
| `MN-285` | task | 8 | TASK :: Feat :: Настройки :: Сверху над кнопкой перехода в режим "Настройки" релизовать "переключатель" светлая/тёмная тема - Toggle-Switch | Wave 7 outputs | compileall; pytest tests -k tasks | Revert MN-285 patch and keep previous behavior |
| `MN-286` | task | 8 | TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Объекты" сделать по подобию навигации "Список задач" - превью в каждой строчке | Wave 7 outputs | compileall; pytest tests -k tasks | Revert MN-286 patch and keep previous behavior |
| `MN-287` | task | 8 | TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Заметки" сделать по подобию навигации "Список задач" - превью в каждой строчке | Wave 7 outputs | compileall; pytest tests -k tasks | Revert MN-287 patch and keep previous behavior |
| `MN-288` | task | 8 | TASK :: Remaster :: View :: Worksapce`s :: Навигацию внутри режима "Идеи" сделать по подобию навигации "Список задач" - превью в каждой строчке | Wave 7 outputs | compileall; pytest tests -k tasks | Revert MN-288 patch and keep previous behavior |
| `MN-289` | partition | 9 | ## PARTITION :: PARSE_DATA :: Импортировать в "Покупки" следующий список товаров со всеми свойствами; https://krasnoyarsk.e2e4online.ru/catalog/item/633334/ | Wave 8 outputs | compileall; pytest tests -k purchases | Revert MN-289 patch and keep previous behavior |

## Delivery Rules For This Sprint
- Implement partition branches per execution wave and avoid overlapping write scopes.
- Run `python -m compileall mindnavigator main.py` before focused tests.
- Run focused tests first using `PYTHONPATH=. pytest tests -k <scope> -p no:cacheprovider --basetemp .pytest_dir/run_tmp`.
- Sync `docs/PARITY.md`, `.codex/HISTORY_TASK.md`, and `.codex/HISTORY_ACTION.md` as each task is completed.
- When Telegram utility is unavailable, log the failed attempt and proceed with direct operator update.

## Execution Progress
- `2026-03-06`: Completed `MN-264` partition closure (`MN-264`, `MN-265`, `MN-266`, `MN-267`) on branch `sprint/mn-195-p264`.
- Validation for closure:
- `python -m compileall mindnavigator main.py`
- `PYTHONPATH=. pytest tests/test_entity_api.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`12 passed`)
- MindNavigator sync:
- updated recursive source statuses for `MN-264..MN-267` to `done=1`.
- Telegram notify:
- attempted `where.exe TellYourCodex`, utility missing in current environment.
