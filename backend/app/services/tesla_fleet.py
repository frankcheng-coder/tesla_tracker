"""Tesla Fleet API client — READ-ONLY data access.

This is the path for connecting a real Tesla account. It only ever calls
read endpoints:

  * GET /api/1/vehicles                         (list vehicles)
  * GET /api/1/vehicles/{id}/vehicle_data       (current state snapshot)

It NEVER calls any command endpoint (no /command/*). There is intentionally no
method here that locks, unlocks, starts climate, charges, honks, or summons.

Because Tesla provides no historical-trip endpoint, the strategy is:
poll `vehicle_data` on an interval -> store each snapshot as a location_point
-> let the trip-reconstruction worker rebuild trips going forward.

TODO(you): to use this against a real account you must have completed the
Tesla Developer setup and obtained an OAuth access token (see services.
tesla_oauth and the README "Connect your own Tesla"). Without credentials the
rest of the app keeps working on mock data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.schemas.models import TelemetryPointIn

log = logging.getLogger(__name__)
settings = get_settings()

# Read-only vehicle_data sections we request. `location_data` requires the
# `vehicle_location` scope. None of these are command endpoints.
VEHICLE_DATA_ENDPOINTS = "location_data;drive_state;charge_state;vehicle_state"


class TeslaFleetClient:
    def __init__(self, access_token: str, audience: str | None = None):
        # TODO(you): `access_token` must be a valid Fleet API OAuth token with
        # scopes `vehicle_device_data` + `vehicle_location`. Obtain it via the
        # OAuth flow in services.tesla_oauth.
        self._token = access_token
        self._base = (audience or settings.tesla_audience).rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def list_vehicles(self) -> list[dict]:
        """Return the raw vehicle list for the authenticated account."""
        url = f"{self._base}/api/1/vehicles"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("response", [])

    async def get_vehicle_data(self, vehicle_tag: str) -> dict:
        """Fetch a current read-only snapshot for one vehicle.

        ``vehicle_tag`` is the Fleet API vehicle id (or VIN). The vehicle must
        be awake; if it is asleep Tesla returns 408 and you simply skip this
        poll (we do NOT send a wake command — that would not be read-only).
        """
        url = f"{self._base}/api/1/vehicles/{vehicle_tag}/vehicle_data"
        params = {"endpoints": VEHICLE_DATA_ENDPOINTS}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers, params=params)
            resp.raise_for_status()
            return resp.json().get("response", {})


def _shift_to_gear(shift_state: str | None) -> str | None:
    if not shift_state:
        return None
    s = shift_state.upper()
    return s if s in {"P", "R", "N", "D"} else None


def vehicle_data_to_point(data: dict) -> TelemetryPointIn | None:
    """Normalize a Fleet API vehicle_data snapshot into one telemetry point.

    Returns None when the snapshot has no usable GPS fix.
    """
    drive = data.get("drive_state", {}) or {}
    charge = data.get("charge_state", {}) or {}
    veh = data.get("vehicle_state", {}) or {}

    lat = drive.get("latitude")
    lon = drive.get("longitude")
    if lat is None or lon is None:
        return None

    # Tesla `drive_state.timestamp` is epoch milliseconds; fall back to now.
    ts_ms = drive.get("timestamp")
    ts = (
        datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        if ts_ms
        else datetime.now(timezone.utc)
    )

    return TelemetryPointIn(
        timestamp=ts,
        latitude=lat,
        longitude=lon,
        speed_mph=drive.get("speed"),          # mph, null when parked
        heading=drive.get("heading"),
        gear=_shift_to_gear(drive.get("shift_state")),
        odometer_miles=veh.get("odometer"),    # miles
        battery_percent=charge.get("battery_level"),
        charge_state=charge.get("charging_state"),
    )
