"""Pydantic API schemas (request/response shapes)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Vehicles ----------------------------------------------------------------
class VehicleOut(ORMModel):
    id: str
    vin: str
    display_name: str | None = None
    tesla_vehicle_id: str | None = None
    tracking_enabled: bool = False
    tracking_paused: bool = False


# --- Trips -------------------------------------------------------------------
class TripOut(ORMModel):
    id: str
    vehicle_id: str
    start_time: datetime
    end_time: datetime
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    start_place_name: str | None = None
    end_place_name: str | None = None
    start_odometer_miles: float | None = None
    end_odometer_miles: float | None = None
    distance_miles: float
    duration_seconds: int
    avg_speed_mph: float | None = None
    max_speed_mph: float | None = None
    start_battery_percent: float | None = None
    end_battery_percent: float | None = None


class TripRouteOut(BaseModel):
    trip_id: str
    route_polyline: str | None = None
    route_geojson: str | None = None


# --- Parking -----------------------------------------------------------------
class ParkingEventOut(ORMModel):
    id: str
    vehicle_id: str
    started_at: datetime
    ended_at: datetime | None = None
    latitude: float
    longitude: float
    place_name: str | None = None
    duration_seconds: int | None = None


# --- Map history -------------------------------------------------------------
class TimelineEntry(BaseModel):
    time: datetime
    event: str


class MapHistoryOut(BaseModel):
    date: str
    trips: list[TripOut]
    parking_events: list[ParkingEventOut]
    timeline: list[TimelineEntry]


# --- Telemetry ingest --------------------------------------------------------
class TelemetryPointIn(BaseModel):
    timestamp: datetime
    latitude: float
    longitude: float
    speed_mph: float | None = None
    heading: float | None = None
    gear: str | None = None
    odometer_miles: float | None = None
    battery_percent: float | None = None
    charge_state: str | None = None


class TelemetryIngestIn(BaseModel):
    vehicle_id: str | None = None
    vin: str | None = None
    points: list[TelemetryPointIn] = Field(default_factory=list)


class TelemetryIngestOut(BaseModel):
    accepted: int
    trips_rebuilt: int
    parking_events_rebuilt: int


# --- Privacy -----------------------------------------------------------------
class PrivacyZoneIn(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius_meters: float = 150.0
    hide_exact_location: bool = True


class PrivacyZoneOut(ORMModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    hide_exact_location: bool


# --- Auth --------------------------------------------------------------------
class AuthStartOut(BaseModel):
    authorize_url: str
    state: str


class SimpleMessage(BaseModel):
    message: str
