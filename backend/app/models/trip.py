"""A reconstructed trip between two parking events."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[str] = uuid_pk()
    vehicle_id: Mapped[str] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    start_latitude: Mapped[float] = mapped_column(Float)
    start_longitude: Mapped[float] = mapped_column(Float)
    end_latitude: Mapped[float] = mapped_column(Float)
    end_longitude: Mapped[float] = mapped_column(Float)

    start_place_name: Mapped[str | None] = mapped_column(String(255))
    end_place_name: Mapped[str | None] = mapped_column(String(255))

    start_odometer_miles: Mapped[float | None] = mapped_column(Float)
    end_odometer_miles: Mapped[float | None] = mapped_column(Float)

    distance_miles: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    avg_speed_mph: Mapped[float | None] = mapped_column(Float)
    max_speed_mph: Mapped[float | None] = mapped_column(Float)

    start_battery_percent: Mapped[float | None] = mapped_column(Float)
    end_battery_percent: Mapped[float | None] = mapped_column(Float)

    # Encoded polyline (Google format) and GeoJSON LineString for map rendering.
    route_polyline: Mapped[str | None] = mapped_column(Text)
    route_geojson: Mapped[str | None] = mapped_column(Text)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="trips")
