from __future__ import annotations

from typing import Any

import httpx

from .auth import SchwabAuthenticator

API_BASE_URL = "https://api.schwabapi.com"


class SchwabApiError(RuntimeError):
    """A Schwab API request failed."""


class SchwabClient:
    def __init__(self, authenticator: SchwabAuthenticator, client: httpx.Client | None = None) -> None:
        self.authenticator = authenticator
        self.client = client or httpx.Client(base_url=API_BASE_URL, timeout=20)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self.client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {self.authenticator.access_token()}"},
        )
        try:
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SchwabApiError(f"Schwab API GET {path} failed with status {response.status_code}.") from exc
