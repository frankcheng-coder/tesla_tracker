"""Vehicle list + read-only tracking controls."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Vehicle
from app.schemas.models import SimpleMessage, VehicleOut
from app.services import mock_data

settings = get_settings()
router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles(db: Session = Depends(get_db)) -> list[VehicleOut]:
    """List connected vehicles. Mock data in dev; real DB rows otherwise."""
    if settings.use_mock_data:
        return [VehicleOut(**mock_data.MOCK_VEHICLE)]
    rows = db.scalars(select(Vehicle)).all()
    return [VehicleOut.model_validate(v) for v in rows]


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)) -> VehicleOut:
    if settings.use_mock_data:
        if vehicle_id != mock_data.MOCK_VEHICLE["id"]:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        return VehicleOut(**mock_data.MOCK_VEHICLE)
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return VehicleOut.model_validate(vehicle)


def _set_tracking(
    db: Session, vehicle_id: str, *, enabled: bool | None, paused: bool | None
) -> None:
    if settings.use_mock_data:
        return
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if enabled is not None:
        vehicle.tracking_enabled = enabled
    if paused is not None:
        vehicle.tracking_paused = paused
    db.commit()


@router.post("/{vehicle_id}/enable-tracking", response_model=SimpleMessage)
def enable_tracking(vehicle_id: str, db: Session = Depends(get_db)) -> SimpleMessage:
    _set_tracking(db, vehicle_id, enabled=True, paused=False)
    return SimpleMessage(message=f"Read-only tracking enabled for {vehicle_id}.")


@router.post("/{vehicle_id}/pause-tracking", response_model=SimpleMessage)
def pause_tracking(vehicle_id: str, db: Session = Depends(get_db)) -> SimpleMessage:
    _set_tracking(db, vehicle_id, enabled=None, paused=True)
    return SimpleMessage(message=f"Tracking paused for {vehicle_id}.")


@router.post("/{vehicle_id}/resume-tracking", response_model=SimpleMessage)
def resume_tracking(vehicle_id: str, db: Session = Depends(get_db)) -> SimpleMessage:
    _set_tracking(db, vehicle_id, enabled=None, paused=False)
    return SimpleMessage(message=f"Tracking resumed for {vehicle_id}.")
