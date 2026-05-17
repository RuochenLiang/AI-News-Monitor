from __future__ import annotations

import httpx

from src.utils.http_utils import request_with_retries


def test_request_with_retries_recovers_from_transient_error(monkeypatch):
    calls = {"count": 0}
    monkeypatch.setattr("time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    response = request_with_retries(client, "GET", "https://example.com")

    assert response.json() == {"ok": True}
    assert calls["count"] == 2
