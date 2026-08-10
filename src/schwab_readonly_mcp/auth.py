from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .config import Settings

AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


class AuthenticationError(RuntimeError):
    """Raised when no usable Schwab OAuth token is available."""


class TokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, object]:
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError as exc:
            raise AuthenticationError(
                "No Schwab token found. Run `schwab-readonly-mcp auth` first."
            ) from exc
        except json.JSONDecodeError as exc:
            raise AuthenticationError(f"Token file is invalid JSON: {self.path}") from exc

    def save(self, token: dict[str, object]) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(token, sort_keys=True))
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)


def authorization_url(settings: Settings) -> str:
    return f"{AUTHORIZE_URL}?{urlencode({'client_id': settings.client_id, 'redirect_uri': settings.redirect_uri})}"


def code_from_redirect(redirect_url: str) -> str:
    values = parse_qs(urlparse(redirect_url).query)
    code = values.get("code", [None])[0]
    if not code:
        raise AuthenticationError("The pasted redirect URL does not contain an OAuth `code` parameter.")
    return code


class SchwabAuthenticator:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.store = TokenStore(settings.token_path)
        self.client = client or httpx.Client(timeout=20)

    def exchange_code(self, code: str) -> None:
        response = self.client.post(
            TOKEN_URL,
            auth=(self.settings.client_id, self.settings.client_secret),
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": self.settings.redirect_uri},
        )
        self._save_response(response)

    def access_token(self) -> str:
        token = self.store.load()
        expires_at = token.get("expires_at")
        access_token = token.get("access_token")
        if isinstance(access_token, str) and isinstance(expires_at, (int, float)) and expires_at > time.time() + 60:
            return access_token
        refresh_token = token.get("refresh_token")
        if not isinstance(refresh_token, str):
            raise AuthenticationError("Token is expired and has no refresh token. Run `schwab-readonly-mcp auth`.")
        response = self.client.post(
            TOKEN_URL,
            auth=(self.settings.client_id, self.settings.client_secret),
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
        self._save_response(response, previous=token)
        refreshed = self.store.load().get("access_token")
        if not isinstance(refreshed, str):
            raise AuthenticationError("Schwab token refresh response did not contain an access token.")
        return refreshed

    def _save_response(self, response: httpx.Response, previous: dict[str, object] | None = None) -> None:
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError("Schwab OAuth request failed; re-run authentication and check app settings.") from exc
        if not isinstance(payload.get("access_token"), str) or not isinstance(payload.get("expires_in"), int):
            raise AuthenticationError("Schwab OAuth response lacks a usable access token.")
        if previous and "refresh_token" not in payload and "refresh_token" in previous:
            payload["refresh_token"] = previous["refresh_token"]
        payload["expires_at"] = time.time() + payload["expires_in"]
        self.store.save(payload)
