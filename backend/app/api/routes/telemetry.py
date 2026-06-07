"""Telemetry ingest endpoint (called by the Fleet Telemetry forwarder)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.models import TelemetryIngestIn, TelemetryIngestOut
from app.services import ingest as ingest_service

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.post("/ingest", response_model=TelemetryIngestOut)
def ingest_telemetry(
    payload: TelemetryIngestIn, db: Session = Depends(get_db)
) -> TelemetryIngestOut:
    """Receive normalized telemetry, store it, and rebuild trips.

    This is the only write path for vehicle data. It performs no vehicle
    commands — it strictly consumes location/speed/gear/odometer/SOC samples.
    """
    try:
        accepted, trips, parking = ingest_service.ingest(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TelemetryIngestOut(
        accepted=accepted, trips_rebuilt=trips, parking_events_rebuilt=parking
    )
