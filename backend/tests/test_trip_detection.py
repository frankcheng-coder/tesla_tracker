"""Unit tests for the trip-reconstruction worker (build step 15)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import trip_reconstruction as tr
from app.services.trip_reconstruction import TelemetrySample

T0 = datetime(2026, 6, 6, 9, 0, 0, tzinfo=timezone.utc)


def _t(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _moving_leg(start_min, lat0, lon0, lat1, lon1, n=6, step=1.0, odo_start=100.0):
    """Build n moving samples along a straight line, one per `step` minutes."""
    pts = []
    for i in range(n):
        f = i / (n - 1)
        pts.append(
            TelemetrySample(
                timestamp=_t(start_min + i * step),
                latitude=lat0 + (lat1 - lat0) * f,
                longitude=lon0 + (lon1 - lon0) * f,
                speed_mph=30.0,
                gear="D",
                odometer_miles=odo_start + f * 5.0,
                battery_percent=80.0 - f * 2.0,
            )
        )
    return pts


def _parked(at_min, lat, lon, n=6, step=1.0, odo=105.0):
    return [
        TelemetrySample(
            timestamp=_t(at_min + i * step),
            latitude=lat,
            longitude=lon,
            speed_mph=0.0,
            gear="P",
            odometer_miles=odo,
            battery_percent=78.0,
        )
        for i in range(n)
    ]


def test_single_trip_detected():
    samples = _moving_leg(0, 37.33, -122.03, 37.37, -121.98)
    trips, parking = tr.detect_trips(samples)
    assert len(trips) == 1
    trip = trips[0]
    assert trip.distance_miles > 0.1
    assert trip.duration_seconds == 5 * 60
    assert trip.max_speed_mph == 30.0
    # One open-ended (still parked) event after the only trip.
    assert len(parking) == 1
    assert parking[0].ended_at is None


def test_short_stop_under_5_min_is_merged():
    leg1 = _moving_leg(0, 37.33, -122.03, 37.35, -122.01, odo_start=100.0)
    # 3-minute stop (< 5 min) — should NOT split.
    stop = _parked(5, 37.35, -122.01, n=3, step=1.0, odo=102.5)
    leg2 = _moving_leg(8, 37.35, -122.01, 37.37, -121.98, odo_start=102.5)
    trips, _ = tr.detect_trips(leg1 + stop + leg2)
    assert len(trips) == 1


def test_long_stop_over_5_min_splits_into_two_trips():
    leg1 = _moving_leg(0, 37.33, -122.03, 37.35, -122.01, odo_start=100.0)
    # 7-minute stop (> 5 min) — should split.
    stop = _parked(5, 37.35, -122.01, n=7, step=1.0, odo=102.5)
    leg2 = _moving_leg(12, 37.35, -122.01, 37.37, -121.98, odo_start=102.5)
    trips, parking = tr.detect_trips(leg1 + stop + leg2)
    assert len(trips) == 2
    # A parking event between the two trips plus the trailing open one.
    assert len(parking) == 2
    assert parking[0].ended_at is not None
    assert parking[0].duration_seconds >= 5 * 60


def test_tiny_movement_under_threshold_ignored():
    # ~10 meters total — under 0.1 mile, should not produce a trip.
    samples = _moving_leg(0, 37.3300, -122.0300, 37.30001 + 0.03, -122.0300, n=4)
    samples = [
        TelemetrySample(
            timestamp=_t(i),
            latitude=37.3300 + i * 0.00001,
            longitude=-122.0300,
            speed_mph=2.0,
            gear="D",
            odometer_miles=100.0,
        )
        for i in range(4)
    ]
    trips, _ = tr.detect_trips(samples)
    assert trips == []


def test_odometer_delta_is_preferred_distance():
    samples = _moving_leg(0, 37.33, -122.03, 37.34, -122.02, odo_start=200.0)
    trips, _ = tr.detect_trips(samples)
    assert len(trips) == 1
    # odometer advanced exactly 5.0 across the leg.
    assert abs(trips[0].distance_miles - 5.0) < 1e-6


def test_impossible_gps_jump_is_filtered():
    base = _moving_leg(0, 37.33, -122.03, 37.34, -122.02)
    # Inject a teleport to the other side of the planet for one sample.
    bad = TelemetrySample(
        timestamp=_t(2.5),
        latitude=-33.86,
        longitude=151.20,  # Sydney
        speed_mph=30.0,
        gear="D",
        odometer_miles=102.0,
    )
    cleaned = tr.filter_gps_jumps(sorted(base + [bad], key=lambda s: s.timestamp))
    assert all(s.longitude < 0 for s in cleaned)  # Sydney sample dropped


def test_route_polyline_and_geojson_present():
    samples = _moving_leg(0, 37.33, -122.03, 37.37, -121.98)
    trips, _ = tr.detect_trips(samples)
    trip = trips[0]
    assert isinstance(trip.route_polyline, str) and trip.route_polyline
    assert '"LineString"' in trip.route_geojson
