# P3-06: workspace memory smoke

The smoke runner repeatedly creates, exercises, closes, and deferred-deletes these owners:

- files image preview with eight 1024x768 images;
- map image preview with the same image set;
- `MapCanvas` with an offscreen grab;
- `CollectionsWorkspace` with an isolated empty database.

Each scenario ran for 20 cycles. Python garbage collection and Qt `DeferredDelete` events were processed after every cycle. Windows Working Set was sampled after cleanup, and weak references verified owner destruction.

| Scenario | Start MB | Midpoint MB | Final MB | Warm growth MB | Alive owners |
| --- | ---: | ---: | ---: | ---: | ---: |
| `files_preview` | 77.35 | 88.26 | 88.28 | 0.02 | 0 |
| `map_preview` | 88.28 | 88.26 | 88.26 | 0.00 | 0 |
| `map_canvas` | 88.26 | 87.26 | 87.26 | 0.00 | 0 |
| `collections_workspace` | 90.40 | 93.59 | 93.60 | 0.02 | 0 |

The initial rise in image and collection scenarios is Qt/plugin/allocator warmup. The second half of every scenario is stable, and no Python/Qt owner remains reachable. No runtime cache or lifecycle patch is justified by this measurement.

The runner is diagnostic rather than a strict RSS CI threshold because native allocators may retain released pages and Working Set varies by host. Automated tests assert deterministic lifecycle cleanup (`alive_owners == 0`).
