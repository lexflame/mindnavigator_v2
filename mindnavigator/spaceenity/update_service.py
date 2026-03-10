"""Update-check service based on GitHub releases API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from .http_client import HttpClient, HttpClientError


class UpdateServiceError(RuntimeError):
    """Raised when update check fails or returns invalid data."""


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    published_at: str
    raw_tag: str


class _HttpClientLike(Protocol):
    def fetch(self, url: str, *, use_cache: bool = True):
        ...


def normalize_version(raw: str) -> str:
    value = (raw or "").strip()
    if value.lower().startswith("v"):
        value = value[1:]
    return value.strip()


def _version_key(value: str) -> tuple[int, ...]:
    normalized = normalize_version(value)
    parts = [int(part) for part in re.findall(r"\d+", normalized)]
    if not parts:
        return (0,)
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    latest_key = _version_key(latest)
    current_key = _version_key(current)
    max_len = max(len(latest_key), len(current_key))
    padded_latest = latest_key + (0,) * (max_len - len(latest_key))
    padded_current = current_key + (0,) * (max_len - len(current_key))
    return padded_latest > padded_current


class UpdateService:
    def __init__(
        self,
        *,
        owner: str,
        repository: str,
        http_client: _HttpClientLike | None = None,
    ) -> None:
        self.owner = (owner or "").strip()
        self.repository = (repository or "").strip()
        if not self.owner or not self.repository:
            raise ValueError("owner and repository are required")
        self._http = http_client or HttpClient(user_agent="MindNavigator/Updater", min_domain_interval=0.2)

    @property
    def latest_release_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repository}/releases/latest"

    def check_for_update(self, current_version: str) -> UpdateInfo:
        normalized_current = normalize_version(current_version)
        if not normalized_current:
            raise ValueError("current_version is required")

        try:
            response = self._http.fetch(self.latest_release_api_url, use_cache=False)
        except HttpClientError as exc:
            raise UpdateServiceError(str(exc)) from exc

        if response is None:
            raise UpdateServiceError("Empty response while checking updates")

        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise UpdateServiceError("Invalid release payload") from exc

        raw_tag = str(payload.get("tag_name") or payload.get("name") or "").strip()
        latest_version = normalize_version(raw_tag)
        if not latest_version:
            raise UpdateServiceError("Release payload does not contain version tag")

        release_url = str(payload.get("html_url") or "").strip()
        published_at = str(payload.get("published_at") or "").strip()

        return UpdateInfo(
            current_version=normalized_current,
            latest_version=latest_version,
            update_available=is_newer_version(latest_version, normalized_current),
            release_url=release_url,
            published_at=published_at,
            raw_tag=raw_tag,
        )
