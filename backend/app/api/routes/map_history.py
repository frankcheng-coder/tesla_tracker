"""Date-based map history endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.models import MapHistoryOut
from app.services import mock_data

router = APIRouter(prefix="/api", tags=["map-history"])


@router.get("/vehicles/{vehicle_id}/map-history", response_model=MapHistoryOut)
def map_history(
    vehicle_id: str,
    date: str = Query(..., description="YYYY-MM-DD"),
) -> MapHistoryOut:
    data = mock_data.mock_map_history(date)
    return MapHistoryOut(**data)
