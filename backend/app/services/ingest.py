"""Telemetry ingestion + trip rebuild orchestration (build step 13).

Stores incoming normalized telemetry as ``location_points`` and then rebuilds
the vehicle's ``trips`` and ``parking_events`` from the full point history using
the trip-reconstruction worker.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LocationPoint, ParkingEvent, Trip, Vehicle
from app.schemas.models import TelemetryIngestIn
from app.services import trip_reconstruction as tr


def _resolve_vehicle(db: Session, payload: TelemetryIngestIn) -> Vehicle | None:
    if payload.vehicle_id:
        return db.get(Vehicle, payload.vehicle_id)
    if payload.vin:
        return db.scalar(select(Vehicle).where(Vehicle.vin == payload.vin))
    return None


def store_points(db: Session, vehicle: Vehicle, payload: TelemetryIngestIn) -> int:
    """Persist incoming telemetry points; returns the count stored."""
    count = 0
    for p in payload.points:
        db.add(
            LocationPoint(
                vehicle_id=vehicle.id,
                timestamp=p.timestamp,
                latitude=p.latitude,
                longitude=p.longitude,
                speed_mph=p.speed_mph,
                heading=p.heading,
                gear=p.gear,
                odometer_miles=p.odometer_miles,
                battery_percent=p.battery_percent,
                charge_state=p.charge_state,
                raw_json=json.dumps(p.model_dump(mode="json")),
            )
        )
        count += 1
    db.flush()
    return count


def rebuild_trips(db: Session, vehicle: Vehicle) -> tuple[int, int]:
    """Recompute trips + parking events for a vehicle from all stored points."""
    points = db.scalars(
        select(LocationPoint)
        .where(LocationPoint.vehicle_id == vehicle.id)
        .order_by(LocationPoint.timestamp)
    ).all()

    samples = [
        tr.TelemetrySample(
            timestamp=lp.timestamp,
            latitude=lp.latitude,
            longitude=lp.longitude,
            speed_mph=lp.speed_mph,
            gear=lp.gear,
            odometer_miles=lp.odometer_miles,
            battery_percent=lp.battery_percent,
        )
        for lp in points
    ]

    trips, parkings = tr.detect_trips(samples)

    # Replace existing derived rows (idempotent rebuild).
    for row in db.scalars(select(Trip).where(Trip.vehicle_id == vehicle.id)).all():
        db.delete(row)
    for row in db.scalars(
        select(ParkingEvent).where(ParkingEvent.vehicle_id == vehicle.id)
    ).all():
        db.delete(row)
    db.flush()

    for t in trips:
        db.add(
            Trip(
                vehicle_id=vehicle.id,
                start_time=t.start_time,
                end_time=t.end_time,
                start_latitude=t.start_latitude,
                start_longitude=t.start_longitude,
                end_latitude=t.end_latitude,
                end_longitude=t.end_longitude,
                start_odometer_miles=t.start_odometer_miles,
                end_odometer_miles=t.end_odometer_miles,
                distance_miles=t.distance_miles,
                duration_seconds=t.duration_seconds,
                avg_speed_mph=t.avg_speed_mph,
                max_speed_mph=t.max_speed_mph,
                start_battery_percent=t.start_battery_percent,
                end_battery_percent=t.end_battery_percent,
                route_polyline=t.route_polyline,
                route_geojson=t.route_geojson,
            )
        )
    for p in parkings:
        db.add(
            ParkingEvent(
                vehicle_id=vehicle.id,
                started_at=p.started_at,
                ended_at=p.ended_at,
                latitude=p.latitude,
                longitude=p.longitude,
                duration_seconds=p.duration_seconds,
            )
        )
    db.flush()
    return len(trips), len(parkings)


def ingest(db: Session, payload: TelemetryIngestIn) -> tuple[int, int, int]:
    """Full ingest: store points + rebuild. Returns (accepted, trips, parking)."""
    vehicle = _resolve_vehicle(db, payload)
    if vehicle is None:
        raise ValueError("Unknown vehicle (provide a known vehicle_id or vin)")
    if vehicle.tracking_paused:
        return 0, 0, 0  # respect pause-tracking: silently drop
    accepted = store_points(db, vehicle, payload)
    trips, parking = rebuild_trips(db, vehicle)
    db.commit()
    return accepted, trips, parking
