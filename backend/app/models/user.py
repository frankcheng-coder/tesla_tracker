"""User account, keyed to a Tesla OAuth subject."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.tesla_token import TeslaToken
    from app.models.vehicle import Vehicle
    from app.models.privacy_zone import PrivacyZone


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    tesla_subject: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)

    tesla_token: Mapped["TeslaToken | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    privacy_zones: Mapped[list["PrivacyZone"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
