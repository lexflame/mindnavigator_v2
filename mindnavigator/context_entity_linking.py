"""Context search and linking for capitalized entity mentions."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Callable, Iterable, Optional, Sequence


CONTEXT_LINK_ENTITY_TYPES = {
    "task": "Задача",
    "idea": "Идея",
    "note": "Заметка",
    "object": "Объект",
}

_WORD_RE = re.compile(r"(?<![#@\w])([A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_-]{1,})(?![\w@])", re.UNICODE)
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_EMAIL_RE = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
_HTML_FRAGMENT_RE = re.compile(r"<([A-Za-z][A-Za-z0-9]*)\b[^>]*>.*?</\1>", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>\n]+>")
_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\([^)]+\)")
_EDGE_PUNCTUATION = " \t\r\n.,;:!?()[]{}<>«»\"'`“”„"


@dataclass(frozen=True)
class ContextWord:
    raw: str
    normalized: str
    start: int
    end: int
    field: str = ""


@dataclass(frozen=True)
class ContextEntitySearchResult:
    entity_id: int
    entity_type: str
    title: str
    subtitle: str
    score: float
    matched_field: str


@dataclass(frozen=True)
class ContextLinkResult:
    success: bool
    created: bool = False
    duplicate: bool = False
    link_id: Optional[int] = None
    message: str = ""


@dataclass(frozen=True)
class PendingContextLink:
    target_type: str
    target_id: int
    anchor_text: str
    source_field: str


def _protected_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in (_URL_RE, _EMAIL_RE, _HTML_FRAGMENT_RE, _HTML_TAG_RE, _MARKDOWN_LINK_RE):
        spans.extend((match.start(), match.end()) for match in pattern.finditer(text or ""))
    return spans


def _inside_spans(start: int, end: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def normalize_context_word(word: str) -> str:
    return (word or "").strip(_EDGE_PUNCTUATION).casefold()


def extract_capitalized_words(text: str, field: str = "", *, min_length: int = 3) -> list[ContextWord]:
    if not text:
        return []
    protected = _protected_spans(text)
    words: list[ContextWord] = []
    seen: set[tuple[str, int, int]] = set()
    for match in _WORD_RE.finditer(text):
        raw = match.group(1).strip(_EDGE_PUNCTUATION)
        if len(raw) < min_length or raw.isdigit():
            continue
        if _inside_spans(match.start(1), match.end(1), protected):
            continue
        first = raw[0]
        if not first.isalpha() or not first.isupper():
            continue
        normalized = normalize_context_word(raw)
        if not normalized or normalized.isdigit():
            continue
        key = (normalized, match.start(1), match.end(1))
        if key in seen:
            continue
        seen.add(key)
        words.append(ContextWord(raw=raw, normalized=normalized, start=match.start(1), end=match.end(1), field=field))
    return words


def _trim_label(value: str, limit: int = 64) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)]}…"


def _field_score(query: str, value: str, base: float) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    normalized = text.casefold()
    if normalized == query:
        return min(1.0, base + 0.18)
    if normalized.startswith(query):
        return min(0.94, base + 0.08)
    tokens = {token.casefold() for token in re.findall(r"[A-Za-zА-Яа-яЁё0-9_-]+", text)}
    if query in tokens:
        return min(0.88, base + 0.04)
    if query in normalized:
        return base
    ratio = SequenceMatcher(None, query, normalized).ratio()
    if ratio >= 0.82:
        return min(0.78, base * ratio)
    return 0.0


class ContextEntitySearchService:
    def __init__(self, db) -> None:
        self._db = db

    def search_context_entities(
        self,
        query: str,
        source_entity_type: Optional[str] = None,
        source_entity_id: Optional[int] = None,
        limit: int = 8,
        min_score: float = 0.65,
    ) -> list[ContextEntitySearchResult]:
        normalized_query = normalize_context_word(query)
        if len(normalized_query) < 3:
            return []
        source_type = (source_entity_type or "").strip().lower()
        source_id = int(source_entity_id) if source_entity_id else None
        results: list[ContextEntitySearchResult] = []
        results.extend(self._search_tasks(normalized_query, source_type, source_id))
        results.extend(self._search_ideas(normalized_query, source_type, source_id))
        results.extend(self._search_notes(normalized_query, source_type, source_id))
        results.extend(self._search_objects(normalized_query, source_type, source_id))
        filtered = [result for result in results if result.score >= min_score]
        filtered.sort(key=lambda item: (-item.score, item.entity_type, item.title.casefold(), item.entity_id))
        return filtered[: max(1, int(limit))]

    def _search_tasks(self, query: str, source_type: str, source_id: Optional[int]) -> list[ContextEntitySearchResult]:
        results = []
        for task in self._safe_fetch("fetch_tasks"):
            if source_type == "task" and source_id == int(task.id):
                continue
            fields = [
                ("title", task.title, 0.82),
                ("project_title", getattr(task, "project_title", ""), 0.72),
                ("project_area", getattr(task, "project_area", ""), 0.68),
                ("description", task.description, 0.64),
            ]
            result = self._best_result(query, "task", int(task.id), task.title, "Задача", fields)
            if result is not None:
                results.append(result)
        return results

    def _search_ideas(self, query: str, source_type: str, source_id: Optional[int]) -> list[ContextEntitySearchResult]:
        active = self._safe_fetch("fetch_ideas", archived=False)
        active_ids = {idea.id for idea in active}
        ideas = [*active, *[idea for idea in self._safe_fetch("fetch_ideas", archived=True) if idea.id not in active_ids]]
        results = []
        for idea in ideas:
            if source_type == "idea" and source_id == int(idea.id):
                continue
            fields = [
                ("title", idea.title, 0.82),
                ("summary", idea.summary, 0.72),
                ("source", idea.source, 0.68),
                ("project_title", getattr(idea, "project_title", ""), 0.68),
                ("body_md", idea.body_md, 0.64),
            ]
            result = self._best_result(query, "idea", int(idea.id), idea.title, "Идея", fields)
            if result is not None:
                results.append(result)
        return results

    def _search_notes(self, query: str, source_type: str, source_id: Optional[int]) -> list[ContextEntitySearchResult]:
        results = []
        for note in self._safe_fetch("fetch_notes"):
            if source_type == "note" and source_id == int(note.id):
                continue
            tags = " ".join(getattr(note, "tags", []) or [])
            fields = [
                ("title", note.title, 0.82),
                ("tags", tags, 0.74),
                ("project", note.project, 0.68),
                ("preview", note.preview, 0.64),
            ]
            result = self._best_result(query, "note", int(note.id), note.title, "Заметка", fields)
            if result is not None:
                results.append(result)
        return results

    def _search_objects(self, query: str, source_type: str, source_id: Optional[int]) -> list[ContextEntitySearchResult]:
        results = []
        for obj in self._safe_fetch("fetch_objects"):
            if source_type == "object" and source_id == int(obj.id):
                continue
            fields = [
                ("title", obj.title, 0.82),
                ("catalog", obj.catalog, 0.72),
                ("object_type", obj.object_type, 0.68),
                ("status", obj.status, 0.66),
                ("description", obj.description, 0.64),
            ]
            result = self._best_result(query, "object", int(obj.id), obj.title, "Объект", fields)
            if result is not None:
                results.append(result)
        return results

    def _safe_fetch(self, method_name: str, *args, **kwargs) -> list:
        method = getattr(self._db, method_name, None)
        if not callable(method):
            return []
        return list(method(*args, **kwargs) or [])

    @staticmethod
    def _best_result(
        query: str,
        entity_type: str,
        entity_id: int,
        title: str,
        subtitle: str,
        fields: Iterable[tuple[str, str, float]],
    ) -> Optional[ContextEntitySearchResult]:
        best_score = 0.0
        best_field = ""
        for field_name, value, base in fields:
            score = _field_score(query, value, base)
            if score > best_score:
                best_score = score
                best_field = field_name
        if best_score <= 0:
            return None
        return ContextEntitySearchResult(
            entity_id=entity_id,
            entity_type=entity_type,
            title=(title or "").strip() or f"{subtitle} #{entity_id}",
            subtitle=subtitle,
            score=round(best_score, 3),
            matched_field=best_field,
        )


class ContextEntityLinkService:
    def __init__(self, db) -> None:
        self._db = db

    def create_context_link(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        anchor_text: str,
        source_field: str,
    ) -> ContextLinkResult:
        normalized_source = (source_type or "").strip().lower()
        normalized_target = (target_type or "").strip().lower()
        if normalized_source not in CONTEXT_LINK_ENTITY_TYPES or normalized_target not in CONTEXT_LINK_ENTITY_TYPES:
            return ContextLinkResult(success=False, message="Неподдерживаемый тип связи.")
        if int(source_id) <= 0 or int(target_id) <= 0:
            return ContextLinkResult(success=False, message="Текущая сущность еще не сохранена.")
        if not self._entity_exists(normalized_source, int(source_id)) or not self._entity_exists(
            normalized_target, int(target_id)
        ):
            return ContextLinkResult(success=False, message="Целевая сущность не найдена.")
        existing = self._db.fetch_context_entity_links(
            source_type=normalized_source,
            source_id=int(source_id),
            target_type=normalized_target,
            target_id=int(target_id),
        )
        if any(link.anchor_text == (anchor_text or "").strip() and link.source_field == (source_field or "").strip() for link in existing):
            return ContextLinkResult(success=True, duplicate=True, message="Связь уже существует.")
        try:
            if normalized_source == "task":
                self._db.add_task_attachment(int(source_id), normalized_target, int(target_id))
            elif normalized_source == "idea":
                self._db.add_idea_relation(int(source_id), normalized_target, int(target_id), "related")
            link = self._db.add_context_entity_link(
                normalized_source,
                int(source_id),
                normalized_target,
                int(target_id),
                anchor_text,
                source_field,
            )
        except (ValueError, TypeError) as exc:
            return ContextLinkResult(success=False, message=str(exc) or "Не удалось создать связь.")
        return ContextLinkResult(success=True, created=True, link_id=link.id, message="Связь создана.")

    def _entity_exists(self, entity_type: str, entity_id: int) -> bool:
        fetchers: dict[str, tuple[str, Callable[[object], int]]] = {
            "task": ("fetch_tasks", lambda item: int(item.id)),
            "idea": ("fetch_ideas", lambda item: int(item.id)),
            "note": ("fetch_notes", lambda item: int(item.id)),
            "object": ("fetch_objects", lambda item: int(item.id)),
        }
        if entity_type == "idea":
            active = self._safe_fetch("fetch_ideas", archived=False)
            active_ids = {int(idea.id) for idea in active}
            ideas = [*active, *[idea for idea in self._safe_fetch("fetch_ideas", archived=True) if int(idea.id) not in active_ids]]
            return any(int(idea.id) == int(entity_id) for idea in ideas)
        fetch = fetchers.get(entity_type)
        if fetch is None:
            return False
        method_name, id_getter = fetch
        return any(id_getter(item) == int(entity_id) for item in self._safe_fetch(method_name))

    def _safe_fetch(self, method_name: str, *args, **kwargs) -> list:
        method = getattr(self._db, method_name, None)
        if not callable(method):
            return []
        return list(method(*args, **kwargs) or [])


__all__ = [
    "CONTEXT_LINK_ENTITY_TYPES",
    "ContextEntityLinkService",
    "ContextEntitySearchResult",
    "ContextEntitySearchService",
    "ContextLinkResult",
    "ContextWord",
    "PendingContextLink",
    "extract_capitalized_words",
    "normalize_context_word",
]
