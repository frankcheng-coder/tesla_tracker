"""Vehicle list + read-only tracking controls."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas.models import SimpleMessage, VehicleOut
from app.services import mock_data

settings = get_settings()
router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles() -> list[VehicleOut]:
    """List the connected vehicles (mock data in dev)."""
    return [VehicleOut(**mock_data.MOCK_VEHICLE)]


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: str) -> VehicleOut:
    if vehicle_id != mock_data.MOCK_VEHICLE["id"]:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return VehicleOut(**mock_data.MOCK_VEHICLE)


@router.post("/{vehicle_id}/enable-tracking", response_model=SimpleMessage)
def enable_tracking(vehicle_id: str) -> SimpleMessage:
    return SimpleMessage(message=f"Read-only tracking enabled for {vehicle_id}.")


@router.post("/{vehicle_id}/pause-tracking", response_model=SimpleMessage)
def pause_tracking(vehicle_id: str) -> SimpleMessage:
    return SimpleMessage(message=f"Tracking paused for {vehicle_id}.")


@router.post("/{vehicle_id}/resume-tracking", response_model=SimpleMessage)
def resume_tracking(vehicle_id: str) -> SimpleMessage:
    return SimpleMessage(message=f"Tracking resumed for {vehicle_id}.")
