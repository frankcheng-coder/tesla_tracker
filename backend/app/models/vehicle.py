"""A Tesla vehicle owned by a user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.location_point import LocationPoint
    from app.models.trip import Trip
    from app.models.parking_event import ParkingEvent


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    vin: Mapped[str] = mapped_column(String(17), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    tesla_vehicle_id: Mapped[str | None] = mapped_column(String(64), index=True)

    # Read-only tracking switches (no vehicle commands are ever issued).
    tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tracking_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="vehicles")
    location_points: Mapped[list["LocationPoint"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    trips: Mapped[list["Trip"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
    parking_events: Mapped[list["ParkingEvent"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )
