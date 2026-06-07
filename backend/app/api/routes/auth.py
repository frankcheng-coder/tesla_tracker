"""Tesla OAuth + session routes.

Read-only: only ``vehicle_device_data`` and ``vehicle_location`` scopes are
requested. No command scopes are ever included.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import TeslaToken
from app.schemas.models import AuthStartOut, SimpleMessage
from app.services import tesla_account, tesla_oauth

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/tesla/start", response_model=AuthStartOut)
def tesla_start() -> AuthStartOut:
    """Begin the Tesla OAuth flow; returns the URL the app should open.

    TODO(you): persist the returned ``state`` (e.g. in a signed cookie or a
    short-lived store) and verify it in the callback to prevent CSRF.
    """
    url, state = tesla_oauth.build_authorize_url()
    return AuthStartOut(authorize_url=url, state=state)


@router.get("/tesla/callback")
async def tesla_callback(
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    """OAuth redirect target. Exchanges the code for tokens and stores them
    (encrypted), then syncs the account's vehicle list.

    TODO(you): verify ``state`` matches the value issued in /tesla/start before
    trusting this callback.
    """
    if not code:
        return SimpleMessage(message="Missing authorization code.")

    bundle = await tesla_oauth.exchange_code(code)

    # Single-user self-hosted mode: attach tokens to the one local user.
    user = tesla_account.get_or_create_single_user(db)
    tesla_account.save_tokens(db, user, bundle)
    db.commit()

    # Best-effort: pull the vehicle list now so the app has something to select.
    try:
        vehicles = await tesla_account.sync_vehicles(db, user)
        count = len(vehicles)
    except Exception as exc:  # don't fail the callback on a transient API error
        log.warning("Vehicle sync after auth failed: %s", exc)
        count = 0

    return SimpleMessage(
        message=(
            f"Tesla account connected (scopes: {bundle.scopes}). "
            f"Found {count} vehicle(s). You can return to the app."
        )
    )


@router.post("/logout", response_model=SimpleMessage)
def logout() -> SimpleMessage:
    return SimpleMessage(message="Logged out.")


@router.post("/disconnect-tesla", response_model=SimpleMessage)
def disconnect_tesla(db: Session = Depends(get_db)) -> SimpleMessage:
    """Delete stored Tesla tokens for the local user."""
    db.execute(delete(TeslaToken))
    db.commit()
    return SimpleMessage(message="Tesla account disconnected and tokens deleted.")
