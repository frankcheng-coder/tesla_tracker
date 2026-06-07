"""Trip list / detail / route / delete endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.models import SimpleMessage, TripOut, TripRouteOut
from app.services import mock_data

router = APIRouter(prefix="/api", tags=["trips"])


@router.get("/vehicles/{vehicle_id}/trips", response_model=list[TripOut])
def list_trips(
    vehicle_id: str,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
) -> list[TripOut]:
    """Trips for a vehicle, optionally filtered to an inclusive date range."""
    trips = [t for t in mock_data.mock_trips() if t["vehicle_id"] == vehicle_id]
    if from_:
        trips = [t for t in trips if t["start_time"][:10] >= from_]
    if to:
        trips = [t for t in trips if t["start_time"][:10] <= to]
    return [TripOut(**t) for t in trips]


@router.get("/trips/{trip_id}", response_model=TripOut)
def get_trip(trip_id: str) -> TripOut:
    trip = mock_data.mock_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripOut(**trip)


@router.get("/trips/{trip_id}/route", response_model=TripRouteOut)
def get_trip_route(trip_id: str) -> TripRouteOut:
    trip = mock_data.mock_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return TripRouteOut(
        trip_id=trip_id,
        route_polyline=trip["route_polyline"],
        route_geojson=trip["route_geojson"],
    )


@router.delete("/trips/{trip_id}", response_model=SimpleMessage)
def delete_trip(trip_id: str) -> SimpleMessage:
    if not mock_data.mock_trip(trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")
    return SimpleMessage(message=f"Trip {trip_id} deleted.")
