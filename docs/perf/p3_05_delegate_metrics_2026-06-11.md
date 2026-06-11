# P3-05: task delegate metric caching

Fixture: 100 projects and 5,000 tasks. Manual full-list measurements used 3,931 visible rows at 1,200 px width in offscreen Qt mode.

## Changes

- Reuse the three immutable `QFontMetrics` instances owned by `TasksItemDelegate`.
- Cache expanded-row heights by text width, title, description, and attachment tags with an 8,192-entry bound.
- Cache the three priority fire icons by resolved color and clear color-sensitive caches on theme changes.
- Avoid reading execution-state roles in `sizeHint()` because they do not affect row height.

## Manual full-list comparison

| Operation | Before median | After median |
| --- | ---: | ---: |
| Cold expanded `sizeHint`, 3,931 rows | 678.675 ms | 577.827 ms |
| Repeated expanded `sizeHint`, 3,931 rows | 678.675 ms | 243.308 ms |
| `paint`, 3,931 rows | 8,483.242 ms | 8,208.405 ms |

The layout cache primarily improves repeated Qt size-hint requests. Paint remains dominated by full row rendering and model-role reads, so width/state-dependent rectangles were deliberately left uncached.

## Runner verification

The standard runner now measures 250 expanded task rows. With 10 iterations and 2 warmup runs:

| Operation | p50 ms | p95 ms | Mean ms |
| --- | ---: | ---: | ---: |
| `tasks_delegate_size_hints` | 13.638 | 14.530 | 13.695 |
