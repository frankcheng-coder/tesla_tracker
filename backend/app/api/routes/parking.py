"""Parking-event endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.models import ParkingEventOut
from app.services import mock_data

router = APIRouter(prefix="/api", tags=["parking"])


@router.get(
    "/vehicles/{vehicle_id}/parking-events",
    response_model=list[ParkingEventOut],
)
def list_parking_events(
    vehicle_id: str,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
) -> list[ParkingEventOut]:
    events = [
        e for e in mock_data.mock_parking_events() if e["vehicle_id"] == vehicle_id
    ]
    if from_:
        events = [e for e in events if e["started_at"][:10] >= from_]
    if to:
        events = [e for e in events if e["started_at"][:10] <= to]
    return [ParkingEventOut(**e) for e in events]
