# CODEX TASK: Auto-link + URL parsing in Task Description

## Goal
Support recognizing URLs in task description: auto-create clickable links when user types URL and presses Space, and optionally extract line-start URLs into a links list.

## Definition of Done
- User can type URL + Space and it becomes a link without breaking editing.
- Utility can extract URLs reliably from text.
- Save flow optionally stores extracted links without duplication.

---

## Step 1: Add URL detection utility
**Create:** `mindnavigator/core/utils/url_parser.py`

Implement:
- `extract_urls(text: str) -> list[str]`
- Recognize `http://` and `https://` at start of line OR surrounded by whitespace.
- Trim trailing punctuation `).,;` safely.

Add a basic regex and unit-test-like self-checks if repo has tests; otherwise add a small function docstring examples.

**Acceptance check:**
- extract_urls returns expected URLs for multi-line text.
- No false positives for 'http: //'.


---

## Step 2: Auto-link in QTextEdit on Space (Task description field)
**Modify:** `mindnavigator/ui/forms/task_edit_form.py` (description input widget)

If description uses `QTextEdit` / `QPlainTextEdit`:
- For `QTextEdit`: implement a custom subclass that intercepts keyPressEvent.
- When user types Space, check the word before cursor; if it looks like URL, apply char format as a link (`QTextCharFormat.setAnchor(True)` and `setAnchorHref(url)`) and keep visible text as url.

Rules:
- Must not break undo/redo.
- Only auto-link if URL length >= 8 and starts with http(s)://.

**Acceptance check:**
- Typing a URL then pressing Space converts it into a clickable link (QTextEdit anchor).
- Undo reverts link formatting cleanly.


---

## Step 3: Parse line-start URLs into dedicated links list (optional integration)
**Modify:** task model save flow (where description is saved)

On save, scan description text with `extract_urls` where URL is at line-start and store into `task.links` (if such field exists) OR into a new `task.meta['links']` array.

Rules:
- Do not remove URLs from description automatically.
- De-duplicate links.

**Acceptance check:**
- Saving a description with line-start URLs produces a list of extracted links in the model.
- Repeated saves do not duplicate entries.
