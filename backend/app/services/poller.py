"""Read-only telemetry poller.

The simplest real-data path: periodically fetch each tracked vehicle's
`vehicle_data` snapshot from the Tesla Fleet API, store it as a location point,
and rebuild trips. No Fleet Telemetry streaming infrastructure required.

This polls only; it never wakes the car (a wake call is a command, not a read).
If the car is asleep the poll is skipped.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, Vehicle
from app.schemas.models import TelemetryIngestIn
from app.services import ingest, tesla_account, tesla_fleet

log = logging.getLogger(__name__)


async def poll_vehicle_once(db: Session, user: User, vehicle: Vehicle) -> bool:
    """Fetch one snapshot for a vehicle and ingest it. Returns True if a point
    was stored."""
    if not vehicle.tracking_enabled or vehicle.tracking_paused:
        return False

    access = await tesla_account.get_valid_access_token(db, user)
    if access is None:
        log.warning("No Tesla access token; skipping poll for %s", vehicle.vin)
        return False

    client = tesla_fleet.TeslaFleetClient(access)
    tag = vehicle.tesla_vehicle_id or vehicle.vin
    try:
        data = await client.get_vehicle_data(tag)
    except httpx.HTTPStatusError as exc:
        # 408 => vehicle asleep/offline. Skip without waking it (read-only).
        if exc.response.status_code == 408:
            log.info("Vehicle %s is asleep; skipping poll.", vehicle.vin)
            return False
        raise

    point = tesla_fleet.vehicle_data_to_point(data)
    if point is None:
        return False

    ingest.ingest(db, TelemetryIngestIn(vehicle_id=vehicle.id, points=[point]))
    return True


async def poll_all_once(db: Session) -> int:
    """Poll every tracked vehicle once. Returns the number of points stored."""
    user = db.scalars(select(User)).first()
    if user is None:
        return 0
    stored = 0
    for vehicle in db.scalars(select(Vehicle).where(Vehicle.user_id == user.id)).all():
        if await poll_vehicle_once(db, user, vehicle):
            stored += 1
    return stored
