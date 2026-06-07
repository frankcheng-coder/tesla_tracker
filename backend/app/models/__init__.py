"""SQLAlchemy ORM models.

Importing this package registers every model on the shared declarative
``Base.metadata`` so that Alembic autogenerate and ``create_all`` see them.
"""

from app.models.user import User
from app.models.tesla_token import TeslaToken
from app.models.vehicle import Vehicle
from app.models.location_point import LocationPoint
from app.models.trip import Trip
from app.models.parking_event import ParkingEvent
from app.models.privacy_zone import PrivacyZone

__all__ = [
    "User",
    "TeslaToken",
    "Vehicle",
    "LocationPoint",
    "Trip",
    "ParkingEvent",
    "PrivacyZone",
]
