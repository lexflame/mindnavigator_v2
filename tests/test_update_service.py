from __future__ import annotations

import pytest

from mindnavigator.http_client import HttpClientError
from mindnavigator.update_service import UpdateService, UpdateServiceError, is_newer_version, normalize_version


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeHttpClient:
    def __init__(self, payload_text: str | None = None, error: Exception | None = None) -> None:
        self._payload_text = payload_text
        self._error = error
        self.requested_urls: list[str] = []

    def fetch(self, url: str, *, use_cache: bool = True):
        self.requested_urls.append(url)
        if self._error is not None:
            raise self._error
        if self._payload_text is None:
            return None
        return _FakeResponse(self._payload_text)


def test_version_normalization_and_comparison() -> None:
    assert normalize_version(" v1.2.3 ") == "1.2.3"
    assert is_newer_version("v1.2.4", "1.2.3") is True
    assert is_newer_version("1.2.3", "v1.2.3") is False
    assert is_newer_version("1.10.0", "1.9.9") is True


def test_check_for_update_returns_latest_release_info() -> None:
    payload = (
        '{"tag_name":"v1.5.0","html_url":"https://github.com/org/repo/releases/tag/v1.5.0",'
        '"published_at":"2026-02-24T10:00:00Z"}'
    )
    fake_http = _FakeHttpClient(payload_text=payload)
    service = UpdateService(owner="org", repository="repo", http_client=fake_http)

    info = service.check_for_update("1.4.9")

    assert info.latest_version == "1.5.0"
    assert info.current_version == "1.4.9"
    assert info.update_available is True
    assert info.release_url.endswith("/v1.5.0")
    assert fake_http.requested_urls == [service.latest_release_api_url]


def test_check_for_update_raises_on_invalid_payload() -> None:
    service = UpdateService(owner="org", repository="repo", http_client=_FakeHttpClient(payload_text="{}"))

    with pytest.raises(UpdateServiceError):
        service.check_for_update("1.0.0")


def test_check_for_update_wraps_http_errors() -> None:
    fake_http = _FakeHttpClient(error=HttpClientError("network down"))
    service = UpdateService(owner="org", repository="repo", http_client=fake_http)

    with pytest.raises(UpdateServiceError):
        service.check_for_update("1.0.0")
