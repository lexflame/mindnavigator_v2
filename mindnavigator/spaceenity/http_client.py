"""HTTP client with retries, cache, and per-domain rate limiting."""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str
    from_cache: bool
    fetched_at: str


@dataclass(frozen=True)
class HttpCacheEntry:
    url: str
    etag: str
    last_modified: str
    body_hash: str
    saved_at: str
    content: bytes


class HttpClientError(RuntimeError):
    pass


class HttpCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS http_cache (
                    url TEXT PRIMARY KEY,
                    etag TEXT NOT NULL DEFAULT '',
                    last_modified TEXT NOT NULL DEFAULT '',
                    body_hash TEXT NOT NULL DEFAULT '',
                    saved_at TEXT NOT NULL,
                    content BLOB NOT NULL
                );
                """
            )

    def get(self, url: str) -> Optional[HttpCacheEntry]:
        row = self._conn.execute(
            """
            SELECT url, etag, last_modified, body_hash, saved_at, content
            FROM http_cache
            WHERE url = ?;
            """,
            (url,),
        ).fetchone()
        if row is None:
            return None
        return HttpCacheEntry(
            row["url"],
            row["etag"] or "",
            row["last_modified"] or "",
            row["body_hash"] or "",
            row["saved_at"],
            row["content"],
        )

    def set(self, entry: HttpCacheEntry) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO http_cache (url, etag, last_modified, body_hash, saved_at, content)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    etag = excluded.etag,
                    last_modified = excluded.last_modified,
                    body_hash = excluded.body_hash,
                    saved_at = excluded.saved_at,
                    content = excluded.content;
                """,
                (
                    entry.url,
                    entry.etag,
                    entry.last_modified,
                    entry.body_hash,
                    entry.saved_at,
                    entry.content,
                ),
            )


class DomainRateLimiter:
    def __init__(self, min_interval: float = 1.0) -> None:
        self._min_interval = max(0.0, float(min_interval))
        self._last_request: dict[str, float] = {}

    def wait(self, domain: str) -> None:
        if not domain or self._min_interval <= 0:
            return
        now = time.monotonic()
        last = self._last_request.get(domain, 0.0)
        delta = now - last
        if delta < self._min_interval:
            time.sleep(self._min_interval - delta)
        self._last_request[domain] = time.monotonic()


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 15.0,
        max_retries: int = 2,
        backoff_seconds: float = 1.2,
        user_agent: str = "MindNavigator/1.0",
        cache_path: Optional[Path] = None,
        min_domain_interval: float = 1.0,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.timeout = float(timeout)
        self.max_retries = max(0, int(max_retries))
        self.backoff_seconds = max(0.0, float(backoff_seconds))
        self.user_agent = user_agent
        self._on_error = on_error
        self._rate_limiter = DomainRateLimiter(min_interval=min_domain_interval)

        if cache_path is None:
            base = Path.home() / ".mindnavigator"
            base.mkdir(parents=True, exist_ok=True)
            cache_path = base / "http_cache.db"
        self.cache = HttpCache(cache_path)

    def fetch(self, url: str, *, use_cache: bool = True) -> HttpResponse | None:
        url = (url or "").strip()
        if not url:
            raise HttpClientError("URL must not be empty.")

        cache_entry = self.cache.get(url) if use_cache else None
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }
        if cache_entry is not None:
            if cache_entry.etag:
                headers["If-None-Match"] = cache_entry.etag
            if cache_entry.last_modified:
                headers["If-Modified-Since"] = cache_entry.last_modified

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        attempt = 0
        while True:
            if domain:
                self._rate_limiter.wait(domain)
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=self.timeout) as response:
                    status = int(getattr(response, "status", 200))
                    resp_headers = {k: v for k, v in response.headers.items()}
                    if status == 304 and cache_entry is not None:
                        return HttpResponse(
                            url=url,
                            status_code=304,
                            headers=resp_headers,
                            content=cache_entry.content,
                            text=_decode_content(cache_entry.content, resp_headers),
                            from_cache=True,
                            fetched_at=cache_entry.saved_at,
                        )
                    body = response.read()
                    text = _decode_content(body, resp_headers)
                    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    if use_cache:
                        etag = resp_headers.get("ETag", "")
                        last_modified = resp_headers.get("Last-Modified", "")
                        body_hash = hashlib.sha256(body).hexdigest()
                        self.cache.set(
                            HttpCacheEntry(
                                url=url,
                                etag=etag,
                                last_modified=last_modified,
                                body_hash=body_hash,
                                saved_at=fetched_at,
                                content=body,
                            )
                        )
                    return HttpResponse(
                        url=url,
                        status_code=status,
                        headers=resp_headers,
                        content=body,
                        text=text,
                        from_cache=False,
                        fetched_at=fetched_at,
                    )
            except HTTPError as exc:
                status = getattr(exc, "code", 0)
                if status == 304 and cache_entry is not None:
                    return HttpResponse(
                        url=url,
                        status_code=304,
                        headers=dict(exc.headers.items()),
                        content=cache_entry.content,
                        text=_decode_content(cache_entry.content, dict(exc.headers.items())),
                        from_cache=True,
                        fetched_at=cache_entry.saved_at,
                    )
                if status >= 500 and attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                    attempt += 1
                    continue
                message = f"HTTP error {status} for {url}"
                self._report_error(message)
                raise HttpClientError(message) from exc
            except URLError as exc:
                if attempt < self.max_retries:
                    self._sleep_backoff(attempt)
                    attempt += 1
                    continue
                message = f"Network error for {url}: {exc}"
                self._report_error(message)
                raise HttpClientError(message) from exc

    def _sleep_backoff(self, attempt: int) -> None:
        if self.backoff_seconds <= 0:
            return
        time.sleep(self.backoff_seconds * (attempt + 1))

    def _report_error(self, message: str) -> None:
        if self._on_error is not None:
            self._on_error(message)


def _decode_content(content: bytes, headers: dict[str, str]) -> str:
    charset = ""
    content_type = headers.get("Content-Type", "")
    if "charset=" in content_type:
        charset = content_type.split("charset=", 1)[1].split(";")[0].strip()
    if not charset:
        charset = "utf-8"
    try:
        return content.decode(charset, errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")
