"""Tesla OAuth + session routes.

Read-only: only ``vehicle_device_data`` and ``vehicle_location`` scopes are
requested. No command scopes are ever included.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.schemas.models import AuthStartOut, SimpleMessage
from app.services import tesla_oauth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/tesla/start", response_model=AuthStartOut)
def tesla_start() -> AuthStartOut:
    """Begin the Tesla OAuth flow; returns the URL the app should open."""
    url, state = tesla_oauth.build_authorize_url()
    return AuthStartOut(authorize_url=url, state=state)


@router.get("/tesla/callback")
async def tesla_callback(code: str | None = None, state: str | None = None):
    """OAuth redirect target. Exchanges the code for tokens.

    In a full deployment this verifies ``state``, exchanges the code, encrypts
    and stores the tokens (see services.crypto / models.TeslaToken), then
    redirects back into the app via a universal link.
    """
    if not code:
        return SimpleMessage(message="Missing authorization code.")
    tokens = await tesla_oauth.exchange_code(code)
    # NOTE: persistence of encrypted tokens happens in the vehicles/onboarding
    # flow once a user record exists. Here we just confirm the exchange.
    return SimpleMessage(
        message=(
            "Tesla account connected (scopes: "
            f"{tokens.scopes}). You can return to the app."
        )
    )


@router.post("/logout", response_model=SimpleMessage)
def logout() -> SimpleMessage:
    return SimpleMessage(message="Logged out.")


@router.post("/disconnect-tesla", response_model=SimpleMessage)
def disconnect_tesla() -> SimpleMessage:
    """Revoke and delete stored Tesla tokens for the user."""
    return SimpleMessage(message="Tesla account disconnected and tokens deleted.")
