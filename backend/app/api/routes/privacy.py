"""Privacy controls: export, delete-all, and privacy zones."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.models import PrivacyZoneIn, PrivacyZoneOut, SimpleMessage
from app.services import mock_data

router = APIRouter(prefix="/api/privacy", tags=["privacy"])

# In-memory zone store for the mock/dev build. Real build persists to DB.
_ZONES: list[dict] = []
_zone_seq = 0


@router.post("/export")
def export_data() -> StreamingResponse:
    """Export trip history as CSV."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "trip_id",
            "start_time",
            "end_time",
            "start_place",
            "end_place",
            "distance_miles",
            "duration_seconds",
            "avg_speed_mph",
            "max_speed_mph",
            "start_battery_percent",
            "end_battery_percent",
        ]
    )
    for t in mock_data.mock_trips():
        writer.writerow(
            [
                t["id"],
                t["start_time"],
                t["end_time"],
                t["start_place_name"],
                t["end_place_name"],
                t["distance_miles"],
                t["duration_seconds"],
                t["avg_speed_mph"],
                t["max_speed_mph"],
                t["start_battery_percent"],
                t["end_battery_percent"],
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tesla_trips.csv"},
    )


@router.delete("/delete-all", response_model=SimpleMessage)
def delete_all() -> SimpleMessage:
    """Delete all stored trip history, location points, and parking events."""
    _ZONES.clear()
    return SimpleMessage(message="All trip history and location data deleted.")


@router.get("/zones", response_model=list[PrivacyZoneOut])
def list_zones() -> list[PrivacyZoneOut]:
    return [PrivacyZoneOut(**z) for z in _ZONES]


@router.post("/zones", response_model=PrivacyZoneOut)
def create_zone(zone: PrivacyZoneIn) -> PrivacyZoneOut:
    global _zone_seq
    _zone_seq += 1
    record = {"id": f"zone_{_zone_seq:04d}", **zone.model_dump()}
    _ZONES.append(record)
    return PrivacyZoneOut(**record)


@router.delete("/zones/{zone_id}", response_model=SimpleMessage)
def delete_zone(zone_id: str) -> SimpleMessage:
    global _ZONES
    _ZONES[:] = [z for z in _ZONES if z["id"] != zone_id]
    return SimpleMessage(message=f"Privacy zone {zone_id} deleted.")
