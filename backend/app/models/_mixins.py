"""Shared column helpers for ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

# Use string UUIDs so the schema is portable between PostgreSQL (production)
# and SQLite (unit tests for the trip-detection worker).
from sqlalchemy import String


def uuid_pk() -> Mapped[str]:
    return mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utcnow,
        onupdate=utcnow,
    )
