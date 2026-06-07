"""Tesla Fleet API OAuth — placeholder implementation (build step 10).

This wires up the *shape* of the official Tesla OAuth 2.0 authorization-code
flow without requiring real credentials during local development. It requests
ONLY read-only scopes (``vehicle_device_data``, ``vehicle_location``) and never
any command scopes.

When real ``TESLA_CLIENT_ID``/``TESLA_CLIENT_SECRET`` are configured, the
``exchange_code`` and ``refresh`` functions perform real token calls via httpx.
Otherwise they return clearly-labelled mock tokens so the rest of the app can
be exercised end-to-end.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from app.config import get_settings

settings = get_settings()


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: str


def is_configured() -> bool:
    return bool(settings.tesla_client_id and settings.tesla_client_secret)


def build_authorize_url(state: str | None = None) -> tuple[str, str]:
    """Return (authorize_url, state). State should be stored and verified on
    callback to prevent CSRF."""
    state = state or secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": settings.tesla_client_id or "MOCK_CLIENT_ID",
        "redirect_uri": settings.tesla_redirect_uri or "http://localhost:8000/auth/tesla/callback",
        "scope": " ".join(settings.tesla_scopes),
        "state": state,
    }
    return f"{settings.tesla_authorize_url}?{urlencode(params)}", state


async def exchange_code(code: str) -> TokenBundle:
    """Exchange an authorization code for tokens."""
    if not is_configured():
        return _mock_tokens()

    data = {
        "grant_type": "authorization_code",
        "client_id": settings.tesla_client_id,
        "client_secret": settings.tesla_client_secret,
        "code": code,
        "redirect_uri": settings.tesla_redirect_uri,
        "audience": settings.tesla_audience,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.tesla_token_url, data=data)
        resp.raise_for_status()
        return _parse_token_response(resp.json())


async def refresh(refresh_token: str) -> TokenBundle:
    """Refresh an access token using a stored refresh token."""
    if not is_configured():
        return _mock_tokens()

    data = {
        "grant_type": "refresh_token",
        "client_id": settings.tesla_client_id,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.tesla_token_url, data=data)
        resp.raise_for_status()
        return _parse_token_response(resp.json())


def _parse_token_response(payload: dict) -> TokenBundle:
    expires_in = int(payload.get("expires_in", 28800))
    return TokenBundle(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token", ""),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        scopes=payload.get("scope", " ".join(settings.tesla_scopes)),
    )


def _mock_tokens() -> TokenBundle:
    return TokenBundle(
        access_token="MOCK_ACCESS_TOKEN_" + secrets.token_hex(8),
        refresh_token="MOCK_REFRESH_TOKEN_" + secrets.token_hex(8),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        scopes=" ".join(settings.tesla_scopes),
    )
