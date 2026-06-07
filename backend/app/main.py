"""FastAPI application entrypoint (build step 1).

Read-only Tesla trip logger backend. Exposes auth, vehicle, telemetry-ingest,
trip, map-history, parking, and privacy routes. No vehicle command endpoints
exist anywhere in this application.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import (
    auth,
    map_history,
    parking,
    privacy,
    telemetry,
    trips,
    vehicles,
    wellknown,
)
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Tesla Trip Logger API",
    version=__version__,
    description=(
        "Private, read-only trip history for your Tesla. "
        "This service never sends commands to a vehicle."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(telemetry.router)
app.include_router(trips.router)
app.include_router(map_history.router)
app.include_router(parking.router)
app.include_router(privacy.router)
app.include_router(wellknown.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "read_only": True,
        "use_mock_data": settings.use_mock_data,
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "Tesla Trip Logger",
        "tagline": "See where your Tesla went.",
        "disclaimer": "This app is not affiliated with Tesla, Inc.",
        "history_note": "History starts from the day you connect your vehicle.",
        "docs": "/docs",
    }
