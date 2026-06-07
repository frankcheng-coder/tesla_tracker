# Tesla Trips — Private trip history for your Tesla

**See where your Tesla went.** A **read-only** trip history and route journal:
automatically build a private record of your Tesla's trips, routes, parking
locations, and mileage.

> This app is read-only. It **never** controls your vehicle — no lock/unlock,
> climate, charging, honk, flash, or summon. It only reads telemetry and builds
> a private trip history.
>
> **History starts from the day you connect your vehicle.** Tesla's API does not
> provide historical trips from before you connect.
>
> _This app is not affiliated with Tesla, Inc._

## Repository layout

| Path        | What it is |
|-------------|------------|
| `backend/`  | FastAPI + PostgreSQL/PostGIS service: OAuth, encrypted token storage, telemetry ingest, trip reconstruction, trip/parking/map-history APIs. |
| `ios/`      | SwiftUI iOS 17+ app: onboarding, trip history, trip detail (MapKit), map history, settings. Runs against a mock API client out of the box. |
| `docker-compose.yml` | Local PostGIS database. |

## Quick start

### 1. Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in values (see backend/README.md)
pytest                          # runs trip-detection unit tests
uvicorn app.main:app --reload   # serves mock data at http://localhost:8000/docs
```
The API serves the six canonical mock trips immediately — no database or Tesla
credentials required — so the iOS app can be developed end-to-end.

For real persistence + telemetry ingest:
```bash
docker compose up -d            # PostGIS on :5432
cd backend && alembic upgrade head
```

### 2. iOS app
```bash
cd ios/TeslaTripLogger
brew install xcodegen            # if needed
xcodegen generate
open TeslaTripLogger.xcodeproj   # ⌘R to run in the simulator
```
The app defaults to the **mock API client** (`APIMode.default` in
`AppEnvironment.swift`), so it runs with no backend. To use the live backend,
set it to `.live(URL(string: "http://localhost:8000")!)`.

## What it answers
- Where did my Tesla go, and when?
- What route did it take, and how long / how far was each trip?
- Where did it park, and for how long?

## Privacy
Delete all data, pause/resume tracking, export CSV, and privacy zones (hide
exact home location). Tesla refresh tokens are encrypted at rest; HTTPS only;
no data sharing or selling; no vehicle commands anywhere in the codebase.

See [`backend/README.md`](backend/README.md) for Tesla Developer setup,
architecture, the trip-detection algorithm, and the full API reference.
