"""Trip reconstruction worker (build step 14).

Turns an ordered stream of telemetry samples for one vehicle into discrete
trips and the parking events between them, following the rules in the plan:

* A trip is *in motion* when ``speed_mph > 1`` or ``gear in {D, R}``.
* A trip ends after the vehicle stays stopped for >= 5 minutes
  (``speed == 0`` and ``gear`` is ``P`` or null).
* Stops shorter than 5 minutes are merged into the same trip.
* Movement under 0.1 mile is ignored (not emitted as a trip).
* Distance prefers the odometer delta, falling back to GPS path length.
* Impossible GPS jumps are filtered before segmentation.
* A parking event spans from one trip's end to the next trip's start.

This module is intentionally free of database/ORM dependencies so it can be
unit-tested in isolation (build step 15).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.services import geo

# --- Tunable thresholds -------------------------------------------------------
SPEED_MOVING_MPH = 1.0
STOP_END_SECONDS = 5 * 60          # >= 5 min stopped ends a trip
HARD_SPLIT_SECONDS = 10 * 60       # >= 10 min stopped always splits trips
MIN_TRIP_DISTANCE_MILES = 0.1
MAX_PLAUSIBLE_SPEED_MPH = 200.0    # implied speeds above this => bad GPS sample


@dataclass
class TelemetrySample:
    """Normalized telemetry input to the worker."""

    timestamp: datetime
    latitude: float
    longitude: float
    speed_mph: float | None = None
    gear: str | None = None
    odometer_miles: float | None = None
    battery_percent: float | None = None


@dataclass
class DetectedTrip:
    start_time: datetime
    end_time: datetime
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    distance_miles: float
    duration_seconds: int
    avg_speed_mph: float | None
    max_speed_mph: float | None
    start_odometer_miles: float | None
    end_odometer_miles: float | None
    start_battery_percent: float | None
    end_battery_percent: float | None
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def route_polyline(self) -> str:
        return geo.encode_polyline(self.points)

    @property
    def route_geojson(self) -> str:
        return geo.to_geojson_linestring(self.points)


@dataclass
class DetectedParking:
    started_at: datetime
    ended_at: datetime | None
    latitude: float
    longitude: float
    duration_seconds: int | None


def _is_moving(s: TelemetrySample) -> bool:
    if s.gear and s.gear.upper() in {"D", "R"}:
        return True
    if s.speed_mph is not None and s.speed_mph > SPEED_MOVING_MPH:
        return True
    return False


def filter_gps_jumps(samples: list[TelemetrySample]) -> list[TelemetrySample]:
    """Drop samples that imply a physically impossible speed from the previous
    accepted sample (teleport/bad-fix outliers)."""
    if not samples:
        return []
    cleaned = [samples[0]]
    for s in samples[1:]:
        prev = cleaned[-1]
        dt_hours = (s.timestamp - prev.timestamp).total_seconds() / 3600.0
        if dt_hours <= 0:
            # Non-increasing timestamp: keep order stable, skip duplicate/backward.
            continue
        dist = geo.haversine_miles(
            prev.latitude, prev.longitude, s.latitude, s.longitude
        )
        if dist / dt_hours > MAX_PLAUSIBLE_SPEED_MPH:
            continue  # impossible jump — discard this sample
        cleaned.append(s)
    return cleaned


def _build_trip(points: list[TelemetrySample]) -> DetectedTrip | None:
    """Construct a DetectedTrip from in-motion samples, or None if too short."""
    if len(points) < 2:
        return None

    coords = [(p.latitude, p.longitude) for p in points]

    # Distance: prefer odometer delta, fall back to GPS path length.
    start_odo = points[0].odometer_miles
    end_odo = points[-1].odometer_miles
    if start_odo is not None and end_odo is not None and end_odo >= start_odo:
        distance = end_odo - start_odo
        if distance == 0:  # odometer didn't tick — trust GPS instead
            distance = geo.path_length_miles(coords)
    else:
        distance = geo.path_length_miles(coords)

    if distance < MIN_TRIP_DISTANCE_MILES:
        return None

    duration = int((points[-1].timestamp - points[0].timestamp).total_seconds())
    speeds = [p.speed_mph for p in points if p.speed_mph is not None]
    max_speed = max(speeds) if speeds else None
    avg_speed = (distance / (duration / 3600.0)) if duration > 0 else None

    # Simplify the route so stored geometry stays compact.
    simplified = geo.douglas_peucker(coords)

    return DetectedTrip(
        start_time=points[0].timestamp,
        end_time=points[-1].timestamp,
        start_latitude=points[0].latitude,
        start_longitude=points[0].longitude,
        end_latitude=points[-1].latitude,
        end_longitude=points[-1].longitude,
        distance_miles=round(distance, 3),
        duration_seconds=duration,
        avg_speed_mph=round(avg_speed, 2) if avg_speed is not None else None,
        max_speed_mph=round(max_speed, 2) if max_speed is not None else None,
        start_odometer_miles=start_odo,
        end_odometer_miles=end_odo,
        start_battery_percent=points[0].battery_percent,
        end_battery_percent=points[-1].battery_percent,
        points=simplified,
    )


def detect_trips(
    samples: list[TelemetrySample],
) -> tuple[list[DetectedTrip], list[DetectedParking]]:
    """Segment telemetry into trips and the parking events between them."""
    samples = sorted(samples, key=lambda s: s.timestamp)
    samples = filter_gps_jumps(samples)

    trips: list[DetectedTrip] = []
    current: list[TelemetrySample] = []       # in-motion points of current trip
    pending: list[TelemetrySample] = []       # short-stop points, not yet committed
    last_motion: TelemetrySample | None = None

    for s in samples:
        if _is_moving(s):
            # Motion resumed within the merge window: fold the short stop back in.
            if current and pending:
                current.extend(pending)
            pending = []
            current.append(s)
            last_motion = s
        else:
            if current and last_motion is not None:
                stopped_for = (s.timestamp - last_motion.timestamp).total_seconds()
                if stopped_for >= STOP_END_SECONDS:
                    # Real stop: close the trip at the last motion point and
                    # discard the buffered stop points (they are parking).
                    trip = _build_trip(current)
                    if trip is not None:
                        trips.append(trip)
                    current = []
                    pending = []
                    last_motion = None
                else:
                    # Short stop (< 5 min): hold the point pending in case motion
                    # resumes (then it's merged), otherwise it's dropped on close.
                    pending.append(s)
            # stopped with no active trip => still parked; nothing to do

    if current:
        trip = _build_trip(current)
        if trip is not None:
            trips.append(trip)

    parkings = _build_parking_events(trips)
    return trips, parkings


def _build_parking_events(trips: list[DetectedTrip]) -> list[DetectedParking]:
    """A parking event spans each trip's end to the next trip's start."""
    parkings: list[DetectedParking] = []
    for i, trip in enumerate(trips):
        if i + 1 < len(trips):
            nxt = trips[i + 1]
            duration = int((nxt.start_time - trip.end_time).total_seconds())
            parkings.append(
                DetectedParking(
                    started_at=trip.end_time,
                    ended_at=nxt.start_time,
                    latitude=trip.end_latitude,
                    longitude=trip.end_longitude,
                    duration_seconds=max(duration, 0),
                )
            )
        else:
            # Final, still-parked event (open-ended).
            parkings.append(
                DetectedParking(
                    started_at=trip.end_time,
                    ended_at=None,
                    latitude=trip.end_latitude,
                    longitude=trip.end_longitude,
                    duration_seconds=None,
                )
            )
    return parkings
