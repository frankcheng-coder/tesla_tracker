"""Initial schema: users, tesla_tokens, vehicles, location_points (PostGIS),
trips, parking_events, privacy_zones.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401  (registers tables on Base.metadata)

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # PostGIS extension (no-op if already present / unsupported backend).
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create all model tables from the shared metadata.
    Base.metadata.create_all(bind=bind)

    # Add the PostGIS geography column described in the plan as a generated
    # column derived from latitude/longitude, plus a spatial index.
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE location_points
            ADD COLUMN IF NOT EXISTS location geography(Point, 4326)
            GENERATED ALWAYS AS (
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_location_points_location "
            "ON location_points USING GIST (location)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_location_points_location")
        op.execute("ALTER TABLE location_points DROP COLUMN IF EXISTS location")
    Base.metadata.drop_all(bind=bind)
