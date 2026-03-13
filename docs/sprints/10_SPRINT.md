# Sprint 10: Dossier Mode

## Sprint Status
- Planned: 2026-03-13
- Status: In Progress
- Branch: `sprint/10_dossier_mode`
- Workstream: new workspace mode

## Sprint Goal
Deliver a new `Досье` mode that accumulates and stores structured knowledge about books, films, games, and writers, using a `Задачи`-style workspace layout without project grouping and with first-class cross-entity attachments.

## Product Directives
- Base the visual structure on `Задачи`, but remove the project axis from the UX and data model.
- Support four dossier kinds in the first release: `book`, `film`, `game`, `writer`.
- Keep one unified workspace and one unified list model so type filters and summaries stay cheap.
- Preserve stable desktop behavior and minimize broad refactors outside the new mode plus required integration seams.
- Dossier items must be attachable to `tasks`, `maps`, `markers`, `notes`, `ideas`, `objects`, and `characters`.

## Functional Scope
### 1. Core domain
- Add persistent dossier records with shared fields: title, dossier kind, summary, description, tags, status, rating, source, cover/image, created/updated timestamps.
- Add typed metadata storage for characteristic fields that differ between books, films, games, and writers.
- Keep validation strict enough to prevent malformed structured data, but flexible enough for partial filling.

### 2. Type-specific metadata
- `book`: author display, original title, publication year, genre, language, pages, publisher, series, ISBN.
- `film`: director, release year, runtime, country, franchise/series, format, age rating, genre.
- `game`: developer/studio, publisher, release year, platform list, engine, genre, play status, playtime, series.
- `writer`: birth year, death year, country, language set, primary genres, notable works summary.

### 3. Workspace behavior
- Reuse the visual language of the tasks list: toolbar, list rows, right-click actions, hover/selection states, quick create/edit path.
- Replace project-specific controls with dossier-specific filters: kind, status, rating, tag/search, optional grouping.
- Show concise typed previews inside list rows so the mode remains scannable.

### 4. Cross-entity links
- Provide attach/detach flows to tasks, maps, map markers, notes, ideas, objects, and characters.
- Keep the implementation symmetrical with existing attachment patterns where possible to avoid one-off link handling.
- Expose dossier-linked entities both from Dossier mode and from target-entity dialogs where practical.

## Execution Waves
### 1. Wave 1 - Storage And Domain Foundation
- Objective: define the schema and API surface before any UI work.
- Tasks:
- `TASK_5D9274B1-5C3A-4D42-A8B2-1F0D64A1E221`

### 2. Wave 2 - Workspace Shell And List UX
- Objective: stand up a usable workspace frame that matches `Задачи` without project semantics.
- Tasks:
- `TASK_2F0C63E8-21E8-4E43-8E62-7B7D12E7B632`

### 3. Wave 3 - Typed Editing And Detail Surfaces
- Objective: make each dossier kind editable with characteristic fields and stable validation.
- Tasks:
- `TASK_B8E7A3F2-6E1A-46CB-9F72-3D7A2E9B4C43`

### 4. Wave 4 - Cross-Entity Attachment Layer
- Objective: integrate dossier items into the rest of the product graph.
- Tasks:
- `TASK_7A4D29C6-8B51-4F0A-90D1-2C5E7B8F1D54`

### 5. Wave 5 - Search, Summaries, And Closure
- Objective: finish discovery UX, aggregate behavior, and validation hardening.
- Tasks:
- `TASK_9C1E6A42-3D84-46FE-9A25-6E3B7C2D5F65`
- `TASK_E1A7C5D3-2F66-4E3F-8A11-5D8B3C6E7F76`

## Task Decomposition Matrix
| Task | Type | Wave | Scope | Dependencies | Validation | Rollback |
| --- | --- | --- | --- | --- | --- | --- |
| `TASK_C6D5B8A4-7F43-4E36-A7E3-8A1B6D934D10` | chore | planning | Compose Sprint 10 plan, execution waves, typed dossier scope, validation order, and integration notes. | None | review plan doc; confirm branch and history updates | Replace or revert sprint planning docs/history updates |
| `TASK_5D9274B1-5C3A-4D42-A8B2-1F0D64A1E221` | feat | 1 | Add dossier storage tables or migration path, dataclasses, fetch/create/update/delete methods, typed metadata serialization, and generic link records for supported entities. Probable touch points: `mindnavigator/storage/`, schema migrations, entity API surface if needed. | Sprint 10 plan | `python -m compileall mindnavigator main.py`; focused pytest for storage/entity API; migration smoke against legacy DB | Revert schema patch and storage changes; preserve existing DB behavior |
| `TASK_2F0C63E8-21E8-4E43-8E62-7B7D12E7B632` | feat | 2 | Create `mindnavigator/workspaces/dossier/` package, list model, delegate, toolbar, mode registration in main window, and tasks-inspired workspace shell without projects. | Wave 1 data model | compileall; focused pytest for workspace init and mode switching | Revert new workspace package and main-window registration |
| `TASK_B8E7A3F2-6E1A-46CB-9F72-3D7A2E9B4C43` | feat | 3 | Build dossier create/edit/details dialogs with kind-aware fields, typed validation, preview formatting, and update flows for books, films, games, and writers. | Waves 1-2 | compileall; focused pytest for dialog/model serialization; manual smoke for field switching | Revert dossier dialog/editor files and restore list-only baseline |
| `TASK_7A4D29C6-8B51-4F0A-90D1-2C5E7B8F1D54` | feat | 4 | Implement attach/detach operations between dossier items and tasks/maps/markers/notes/ideas/objects/characters, plus UI entry points and storage consistency rules. | Waves 1-3; existing attachment patterns | compileall; focused pytest for link persistence and UI actions | Revert dossier link schema/UI hooks and keep isolated dossier records |
| `TASK_9C1E6A42-3D84-46FE-9A25-6E3B7C2D5F65` | feat | 5 | Add dossier search, type/status filters, grouping, quick summaries, and “accumulation” behavior for totals by kind, status, rating, or tag. | Waves 1-4 | compileall; focused pytest for filtering/grouping/summaries | Revert search/filter/summarization layer while keeping core dossier CRUD |
| `TASK_E1A7C5D3-2F66-4E3F-8A11-5D8B3C6E7F76` | feat | 5 | Add regression suites, source-inspection tests where useful, release notes, and final validation for Sprint 10 delivery. | Waves 1-5 | `python -m compileall mindnavigator main.py`; focused pytest for dossier/storage/integration; broader `PYTHONPATH=. pytest tests -p no:cacheprovider --basetemp .pytest_dir/run_tmp` when scope stabilizes | Revert only dossier-specific tests/docs if closure packaging must be split from feature work |

## Implementation Notes
- Preferred package target: `mindnavigator/workspaces/dossier/`.
- Expected main-window integration points: workspace mode registration, i18n labels, left-rail visibility map, and startup workspace construction.
- Storage should follow existing UTC timestamp rules and reuse current patterns for dataclasses and SQL helpers.
- For quick actions in dossier list rows, prefer delegate hit-zones over embedded widgets.
- If a generic attachment abstraction can be reused safely, prefer that over adding a second bespoke relationship system.

## Validation Order
1. `python -m compileall mindnavigator main.py`
2. Focused pytest for storage and new dossier workspace modules
3. Focused pytest for each integration surface touched by dossier attachments
4. Broader regression run when the sprint reaches closure state

## Rollback Strategy
- Keep each wave isolated in its own partition branch so rollback can happen at wave granularity.
- Prefer additive migrations and explicit downgrade-safe fallbacks over in-place destructive refactors.
- If cross-entity links destabilize unrelated modes, disable only dossier link entry points first and keep dossier CRUD available.
