"""Mock trip / parking / vehicle data (build step 4).

Lets the iOS app and API be developed before real Tesla Fleet integration is
wired up. Six canonical trips from the plan, around a fictional home base in
the South Bay. Coordinates are realistic but invented.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import geo

# A fixed reference day so the mock output is deterministic.
_DAY = datetime(2026, 6, 6, tzinfo=timezone.utc)

MOCK_VEHICLE = {
    "id": "veh_mock_0001",
    "vin": "5YJ3E1EA7PF000000",
    "display_name": "My Tesla",
    "tesla_vehicle_id": "1000000000000001",
    "tracking_enabled": True,
    "tracking_paused": False,
}

# Named places: (lat, lon)
_PLACES = {
    "Home": (37.3318, -122.0312),
    "Preschool": (37.3505, -122.0250),
    "Costco": (37.3760, -121.9750),
    "Work": (37.3947, -122.1500),
    "Gym": (37.3600, -122.0800),
}


def _interp(a: tuple[float, float], b: tuple[float, float], n: int = 8):
    """A simple straight-line set of intermediate (lat, lon) points."""
    (lat1, lon1), (lat2, lon2) = a, b
    return [
        (lat1 + (lat2 - lat1) * i / (n - 1), lon1 + (lon2 - lon1) * i / (n - 1))
        for i in range(n)
    ]


_LEGS = [
    # (start_place, end_place, start_offset_min, duration_min, batt_start, batt_end)
    ("Home", "Preschool", 8 * 60 + 30, 25, 82, 80),
    ("Preschool", "Costco", 9 * 60 + 10, 18, 80, 78),
    ("Costco", "Home", 10 * 60 + 12, 23, 78, 75),
    ("Home", "Work", 13 * 60 + 0, 35, 90, 84),
    ("Work", "Gym", 17 * 60 + 30, 20, 84, 80),
    ("Gym", "Home", 18 * 60 + 45, 22, 80, 77),
]


def _make_trip(idx: int, leg) -> dict:
    start_place, end_place, start_off, dur, b0, b1 = leg
    a, b = _PLACES[start_place], _PLACES[end_place]
    start = _DAY + timedelta(minutes=start_off)
    end = start + timedelta(minutes=dur)

    pts = _interp(a, b)
    distance = round(geo.path_length_miles(pts), 2)
    avg_speed = round(distance / (dur / 60.0), 1) if dur else 0.0

    return {
        "id": f"trip_mock_{idx:04d}",
        "vehicle_id": MOCK_VEHICLE["id"],
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "start_latitude": a[0],
        "start_longitude": a[1],
        "end_latitude": b[0],
        "end_longitude": b[1],
        "start_place_name": start_place,
        "end_place_name": end_place,
        "start_odometer_miles": 12000.0 + idx * 10,
        "end_odometer_miles": 12000.0 + idx * 10 + distance,
        "distance_miles": distance,
        "duration_seconds": dur * 60,
        "avg_speed_mph": avg_speed,
        "max_speed_mph": round(avg_speed * 1.6, 1),
        "start_battery_percent": float(b0),
        "end_battery_percent": float(b1),
        "route_polyline": geo.encode_polyline(pts),
        "route_geojson": geo.to_geojson_linestring(pts),
    }


def mock_trips() -> list[dict]:
    return [_make_trip(i + 1, leg) for i, leg in enumerate(_LEGS)]


def mock_trip(trip_id: str) -> dict | None:
    return next((t for t in mock_trips() if t["id"] == trip_id), None)


def mock_parking_events() -> list[dict]:
    trips = mock_trips()
    events: list[dict] = []
    for i, t in enumerate(trips):
        started = t["end_time"]
        if i + 1 < len(trips):
            ended = trips[i + 1]["start_time"]
            dur = int(
                (
                    datetime.fromisoformat(ended) - datetime.fromisoformat(started)
                ).total_seconds()
            )
        else:
            ended, dur = None, None
        events.append(
            {
                "id": f"park_mock_{i + 1:04d}",
                "vehicle_id": MOCK_VEHICLE["id"],
                "started_at": started,
                "ended_at": ended,
                "latitude": t["end_latitude"],
                "longitude": t["end_longitude"],
                "place_name": t["end_place_name"],
                "duration_seconds": dur,
            }
        )
    return events


def mock_map_history(date: str) -> dict:
    """All trips + parking + a flat timeline for a given YYYY-MM-DD date."""
    trips = [t for t in mock_trips() if t["start_time"].startswith(date)]
    parking = [
        p for p in mock_parking_events() if p["started_at"].startswith(date)
    ]

    timeline: list[dict] = []
    for t in trips:
        timeline.append(
            {"time": t["start_time"], "event": f"Left {t['start_place_name']}"}
        )
        timeline.append(
            {"time": t["end_time"], "event": f"Arrived at {t['end_place_name']}"}
        )
    timeline.sort(key=lambda e: e["time"])

    return {"date": date, "trips": trips, "parking_events": parking, "timeline": timeline}
