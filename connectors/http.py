from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import APP_VERSION, REQUEST_TIMEOUT_SECONDS

_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


def create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=_RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": f"VOCANTA/{APP_VERSION} job-discovery-client",
            "Accept": "application/json",
        }
    )
    return session


def get_json(session: requests.Session, url: str) -> Any:
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        content_type = response.headers.get("Content-Type", "unknown")
        raise ValueError(
            f"Expected JSON from {url}, received {content_type}"
        ) from exc
