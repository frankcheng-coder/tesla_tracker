"""Geospatial helpers: distance, route simplification, polyline/GeoJSON.

Kept dependency-light (pure math + ``polyline``) so the trip-detection unit
tests don't require PostGIS.
"""

from __future__ import annotations

import json
import math

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(a)))


def path_length_miles(points: list[tuple[float, float]]) -> float:
    """Total length of a (lat, lon) path in miles."""
    return sum(
        haversine_miles(*points[i], *points[i + 1]) for i in range(len(points) - 1)
    )


def _perp_distance(pt, start, end) -> float:
    """Perpendicular distance from ``pt`` to the segment start->end (degrees)."""
    (x, y), (x1, y1), (x2, y2) = pt, start, end
    if (x1, y1) == (x2, y2):
        return math.hypot(x - x1, y - y1)
    dx, dy = x2 - x1, y2 - y1
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    px, py = x1 + t * dx, y1 + t * dy
    return math.hypot(x - px, y - py)


def douglas_peucker(
    points: list[tuple[float, float]], epsilon: float = 0.00005
) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker simplification of a (lat, lon) polyline.

    ``epsilon`` is in degrees (~5.5 m at the equator for the default).
    """
    if len(points) < 3:
        return points[:]

    dmax, index = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perp_distance(points[i], points[0], points[-1])
        if d > dmax:
            dmax, index = d, i

    if dmax > epsilon:
        left = douglas_peucker(points[: index + 1], epsilon)
        right = douglas_peucker(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def encode_polyline(points: list[tuple[float, float]]) -> str:
    """Encode (lat, lon) points to a Google-format polyline string."""
    import polyline as _polyline

    return _polyline.encode(points)


def to_geojson_linestring(points: list[tuple[float, float]]) -> str:
    """Serialize (lat, lon) points to a GeoJSON LineString (lon, lat order)."""
    return json.dumps(
        {
            "type": "LineString",
            "coordinates": [[lon, lat] for lat, lon in points],
        }
    )
