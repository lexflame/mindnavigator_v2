# P3-04: lazy loading decision and 5k verification

Fixture: 100 projects, 5,000 tasks, 1,000 context links, and 2,500 task attachments. Measurements used 10 iterations and 2 warmup runs in offscreen Qt mode.

## Decision

- `TasksModel.refresh()` still builds the complete filtered tree in about 351 ms p95, below the existing 500 ms diagnostic threshold. Partial child fetching would complicate filtering, plan metadata, drag/drop, and parent grouping without a measured UX benefit, so nested-task loading remains unchanged.
- `AttachmentSummary` previously executed one query per rendered task. A manual cold scan of 3,931 rows took 121-128 ms and issued thousands of queries.
- Attachment counts now load lazily on the first summary request with one grouped query and remain cached until model refresh or explicit invalidation.

## Verification

| Operation | p50 ms | p95 ms | Mean ms |
| --- | ---: | ---: | ---: |
| `tasks_model_reload` | 315.493 | 350.651 | 319.088 |
| `task_attachment_summaries` | 42.832 | 50.575 | 44.107 |

The summary benchmark includes model-index and role-access overhead for all 3,931 visible rows. The storage work is a single grouped SQL query instead of one query per row.
