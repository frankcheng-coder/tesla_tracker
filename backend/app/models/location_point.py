"""A single timestamped telemetry sample for a vehicle.

The PostGIS ``location geography(Point, 4326)`` column described in the plan
is added by the Alembic migration as a *generated* column derived from
``latitude``/``longitude`` (kept here as plain floats so the same models work
under SQLite for unit tests).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import uuid_pk, utcnow

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class LocationPoint(Base):
    __tablename__ = "location_points"

    id: Mapped[str] = uuid_pk()
    vehicle_id: Mapped[str] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed_mph: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float)
    gear: Mapped[str | None] = mapped_column(String(8))  # P / R / N / D
    odometer_miles: Mapped[float | None] = mapped_column(Float)
    battery_percent: Mapped[float | None] = mapped_column(Float)
    charge_state: Mapped[str | None] = mapped_column(String(32))
    raw_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    vehicle: Mapped["Vehicle"] = relationship(back_populates="location_points")
