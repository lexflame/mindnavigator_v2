# Sprint 7: Codex Entity API And Delivery Gates

## Sprint Status
- Planned: 2026-03-02

## Sprint Goal
Deliver a Codex-compatible entity API for the desktop application and harden the sprint delivery process so each partition ships behind validated pipeline gates.

## Scope
- Entity API contract for create, read, list, update, delete, and execute operations.
- Codex integration layer that can discover and use the API.
- API pool self-description handshake so connected AI clients can inspect capabilities and interface shape.
- Delivery process rules for partition branches, PR flow, decomposition, commit discipline, and pipeline gates.
- CI pipeline alignment with repository runtime and test constraints.

## Partitions
1. `PARTITION A` - Contract and discovery layer.
2. `PARTITION B` - Entity CRUD surface and storage mapping.
3. `PARTITION C` - Execute/action endpoints and Codex adapter flow.
4. `PARTITION D` - API pool self-description, docs, and release validation.

## Task Array
1. `TASK_GUID: TASK_7F8B3A91-54E3-4A8D-9B51-0A21C2A0F101`
- Type: `chore`
- Workspace: `infra/ci`
- Title: Align GitHub Actions pipeline with project runtime requirements and stable pytest temp handling.
- Partition: `PARTITION A`
- Decomposition:
- move workflows to Python 3.11+ only;
- run compile validation before tests;
- run pytest with `tests -p no:cacheprovider` and runner temp basetemp;
- enforce headless Qt settings for Linux CI.

2. `TASK_GUID: TASK_8C1E4D27-1B3D-4C67-A0B2-31DE8F0D2202`
- Type: `design`
- Workspace: `api/contracts`
- Title: Define the canonical entity API contract for list, get, create, update, delete, and execute actions.
- Partition: `PARTITION A`
- Decomposition:
- enumerate supported entity kinds and shared identifiers;
- define request/response envelopes and error model;
- define pagination, filtering, and optimistic concurrency rules;
- document compatibility expectations for Codex clients.

3. `TASK_GUID: TASK_9A4F0E62-7C85-4A26-8D9E-58C2A56F3303`
- Type: `feat`
- Workspace: `api/transport`
- Title: Implement API bootstrap endpoint that exposes service metadata, version, and endpoint inventory.
- Partition: `PARTITION A`
- Decomposition:
- add handshake endpoint for capability discovery;
- include schema version and supported entity operations;
- include auth/session expectations if any;
- provide machine-readable examples for Codex bootstrapping.

4. `TASK_GUID: TASK_A1B0C6D4-8E21-4F7C-B2E4-6D19C7804404`
- Type: `feat`
- Workspace: `api/entities`
- Title: Implement entity listing and entity read endpoints for all supported application entities.
- Partition: `PARTITION B`
- Decomposition:
- map application entities to a shared DTO surface;
- implement list endpoint with filters and sort options;
- implement read endpoint with full payload expansion;
- add regression tests for empty, nested, and missing-entity cases.

5. `TASK_GUID: TASK_B2C9D8E5-9F32-4A5D-B3F5-72EA1D905505`
- Type: `feat`
- Workspace: `api/entities`
- Title: Implement entity create and update endpoints with validation and backward-safe defaults.
- Partition: `PARTITION B`
- Decomposition:
- validate required and optional fields per entity kind;
- preserve existing defaults and migration-safe behavior;
- return normalized entity payloads after write;
- add tests for validation failures and round-trip persistence.

6. `TASK_GUID: TASK_C3D0E9F6-A143-4B6E-C406-83FB2EA06606`
- Type: `feat`
- Workspace: `api/entities`
- Title: Implement entity delete endpoint with safety guards and explicit failure modes.
- Partition: `PARTITION B`
- Decomposition:
- define hard-delete versus guarded-delete semantics;
- block unsafe deletes when dependencies exist unless explicitly allowed;
- return deterministic error payloads for protected entities;
- add regression tests for parent-child and linked-data cases.

7. `TASK_GUID: TASK_D4E1F0A7-B254-4C7F-D517-94AC3FB17707`
- Type: `feat`
- Workspace: `api/actions`
- Title: Implement entity execute endpoint for domain actions that mutate or trigger application behavior.
- Partition: `PARTITION C`
- Decomposition:
- define executable action registry per entity type;
- implement parameter validation and result envelopes;
- make execution side effects explicit and idempotency rules documented;
- add tests for allowed, denied, and unsupported actions.

8. `TASK_GUID: TASK_E5F2A1B8-C365-4D80-E628-A5BD40C28808`
- Type: `feat`
- Workspace: `codex/adapter`
- Title: Implement Codex adapter layer that discovers the API, negotiates capabilities, and calls entity endpoints.
- Partition: `PARTITION C`
- Decomposition:
- add a discovery flow that reads the API self-description;
- map Codex intents to API endpoints and payloads;
- handle version mismatches and unsupported capabilities gracefully;
- add integration tests for discovery and CRUD/action flows.

9. `TASK_GUID: TASK_F603B2C9-D476-4E91-F739-B6CE51D39909`
- Type: `docs`
- Workspace: `api/docs`
- Title: Publish API pool self-description schema and usage examples for AI clients.
- Partition: `PARTITION D`
- Decomposition:
- document the self-description payload;
- document endpoint catalog and semantic guarantees;
- provide examples for bootstrap, CRUD, and execute flows;
- include versioning and compatibility notes for future clients.

10. `TASK_GUID: TASK_0714C3DA-E587-4FA2-084A-C7DF62E4AA10`
- Type: `chore`
- Workspace: `release/validation`
- Title: Close the sprint with partition-by-partition validation, PR completion, and merge gating.
- Partition: `PARTITION D`
- Decomposition:
- run compile and targeted tests per partition;
- verify pipeline success before advancing;
- open and complete a PR per partition branch;
- document residual risks before sprint closure.

## Validation Matrix
- `PARTITION A`:
- `python -m compileall mindnavigator main.py`
- workflow lint/test smoke on branch
- contract review for API discovery payloads
- `PARTITION B`:
- `python -m compileall mindnavigator main.py`
- targeted pytest for storage and entity API modules
- CRUD regression tests for create/read/update/delete
- `PARTITION C`:
- `python -m compileall mindnavigator main.py`
- targeted pytest for action execution and Codex adapter modules
- integration tests for discovery plus execute flows
- `PARTITION D`:
- full branch pipeline must pass before merge
- docs review for API self-description examples
- final regression sweep for touched modules

## Definition Of Done
- Each sprint task has a written decomposition before implementation starts.
- Each `PARTITION` is delivered from its own branch and completed through a dedicated PR.
- Every change is committed and pushed after validation.
- The next task starts only after the current partition pipeline passes.
- Codex can discover the API, understand the self-description payload, and call CRUD plus execute operations through the documented interface.
