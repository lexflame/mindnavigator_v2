# CODEX TASK: Maps: Hide Small Markers on Zoom-out and Restore on Zoom-in

## Goal
Fix marker visibility: small markers should disappear when zoom is reduced and reappear when zoom increases, using clear thresholds.

## Definition of Done
- Markers hide/show deterministically based on zoom.
- No persistent disappearance bug after zoom changes.
- Optional per-marker visibility override exists.

---

## Step 1: Define zoom-based marker visibility thresholds
**Modify:** map marker rendering code

Introduce rule:
- Markers smaller than a threshold (in pixels or 'marker_size') are hidden when zoom < `min_zoom_to_show`.
- When zoom increases back above threshold, markers reappear.

Implementation:
- Compute effective on-screen size based on marker size * zoom.
- If < 4–6 px, hide.

**Acceptance check:**
- Small markers disappear when zoomed out and reappear when zoomed in.
- No flicker at boundary (use hysteresis optional).


---

## Step 2: Add optional per-marker override
**Modify:** marker model

Add `min_visible_zoom: float | None`.
If set, use it instead of global rule.

**Acceptance check:**
- Per-marker overrides work; default uses global behavior.
