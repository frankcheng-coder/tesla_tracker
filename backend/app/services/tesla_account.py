"""Tesla account/token persistence (single-user self-hosted mode).

Ties together OAuth (services.tesla_oauth), encryption (services.crypto), and
the User/TeslaToken/Vehicle models. Stores tokens ENCRYPTED at rest and hands
back a valid access token, refreshing it when expired.

TODO(you): this assumes ONE Tesla account per deployment (self-hosting your own
trip logger). For a multi-user product you would key everything off an
authenticated session/user id instead of `get_or_create_single_user`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TeslaToken, User, Vehicle
from app.services import crypto, tesla_fleet, tesla_oauth


def get_or_create_single_user(db: Session) -> User:
    user = db.scalars(select(User)).first()
    if user is None:
        user = User(email=None, tesla_subject=None)
        db.add(user)
        db.flush()
    return user


def save_tokens(db: Session, user: User, bundle: tesla_oauth.TokenBundle) -> TeslaToken:
    """Persist an OAuth token bundle, encrypting access + refresh tokens."""
    token = db.scalars(
        select(TeslaToken).where(TeslaToken.user_id == user.id)
    ).first()
    if token is None:
        token = TeslaToken(user_id=user.id)
        db.add(token)
    token.access_token_encrypted = crypto.encrypt(bundle.access_token)
    token.refresh_token_encrypted = crypto.encrypt(bundle.refresh_token)
    token.expires_at = bundle.expires_at
    token.scopes = bundle.scopes
    db.flush()
    return token


async def get_valid_access_token(db: Session, user: User) -> str | None:
    """Return a usable access token, refreshing it if it has (nearly) expired."""
    token = db.scalars(
        select(TeslaToken).where(TeslaToken.user_id == user.id)
    ).first()
    if token is None:
        return None

    expires_at = token.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Refresh if expiring within 2 minutes.
    if expires_at and expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
        refresh_token = crypto.decrypt(token.refresh_token_encrypted)
        bundle = await tesla_oauth.refresh(refresh_token)
        # Tesla may not return a new refresh token; keep the old one if so.
        if not bundle.refresh_token:
            bundle.refresh_token = refresh_token
        token = save_tokens(db, user, bundle)
        db.commit()

    return crypto.decrypt(token.access_token_encrypted)


async def sync_vehicles(db: Session, user: User) -> list[Vehicle]:
    """Pull the account's vehicle list from Tesla and upsert Vehicle rows."""
    access = await get_valid_access_token(db, user)
    if access is None:
        return []

    client = tesla_fleet.TeslaFleetClient(access)
    remote = await client.list_vehicles()

    vehicles: list[Vehicle] = []
    for rv in remote:
        vin = rv.get("vin")
        if not vin:
            continue
        vehicle = db.scalars(
            select(Vehicle).where(Vehicle.user_id == user.id, Vehicle.vin == vin)
        ).first()
        if vehicle is None:
            vehicle = Vehicle(user_id=user.id, vin=vin)
            db.add(vehicle)
        vehicle.display_name = rv.get("display_name") or vehicle.display_name
        vehicle.tesla_vehicle_id = str(rv.get("id") or rv.get("id_s") or "")
        vehicles.append(vehicle)
    db.commit()
    return vehicles
