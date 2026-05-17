from __future__ import annotations

import time
from typing import Any

import httpx


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    retries: int = 2,
    backoff_seconds: float = 0.5,
    **kwargs: Any,
) -> httpx.Response:
    last_error: httpx.HTTPError | None = None
    for attempt in range(retries + 1):
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(backoff_seconds * (2**attempt))
    raise last_error or httpx.HTTPError("HTTP request failed")
