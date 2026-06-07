"""Encrypted Tesla OAuth tokens.

Access and refresh tokens are stored *encrypted* (Fernet) — the plaintext
never touches the database. Only read-only scopes are ever requested.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._mixins import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User


class TeslaToken(Base, TimestampMixin):
    __tablename__ = "tesla_tokens"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str | None] = mapped_column(String(512))

    user: Mapped["User"] = relationship(back_populates="tesla_token")
