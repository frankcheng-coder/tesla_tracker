# Tesla Trips — Backend

Read-only FastAPI service that ingests Tesla telemetry, reconstructs trips, and
serves a private trip history. **No vehicle command endpoints exist anywhere in
this service.**

## Stack
FastAPI · SQLAlchemy 2 · PostgreSQL + PostGIS · Alembic · httpx · cryptography ·
shapely · polyline.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest                          # trip-detection unit tests
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

With `USE_MOCK_DATA=true` (the default), all read endpoints serve six canonical
mock trips and **no database is required**. The telemetry-ingest endpoint and
real persistence require PostGIS:

```bash
docker compose up -d            # from the repo root → PostGIS on :5432
alembic upgrade head            # create schema (PostGIS extension + tables)
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg2://tesla:tesla@localhost:5432/tesla_tracker` |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypting Tesla tokens at rest. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `TESLA_CLIENT_ID` / `TESLA_CLIENT_SECRET` | From the Tesla Developer portal |
| `TESLA_REDIRECT_URI` | OAuth callback, must match the portal config |
| `TESLA_DEVELOPER_DOMAIN` | Your registered developer domain |
| `TESLA_AUDIENCE` | Fleet API base, e.g. `https://fleet-api.prd.na.vn.cloud.tesla.com` |
| `USE_MOCK_DATA` | `true` to serve mock data without Tesla/DB |

## Tesla Developer setup (real data)

1. **Create an app** at <https://developer.tesla.com> → register a new
   application. Note the **Client ID** and **Client Secret**.
2. **Allowed redirect URI** — set it to your `TESLA_REDIRECT_URI`
   (e.g. `https://your-domain.example.com/auth/tesla/callback`).
3. **Scopes (read-only only):** request **`vehicle_device_data`** and
   **`vehicle_location`**. Do **not** request any command scopes
   (`vehicle_cmds`, `vehicle_charging_cmds`, etc.).
4. **Developer domain & public key.** Tesla requires you to host a public key at
   `https://<your-domain>/.well-known/appspecific/com.tesla.3p.public-key.pem`.
   Generate an EC key pair and publish the public key:
   ```bash
   openssl ecparam -name prime256v1 -genkey -noout -out private-key.pem
   openssl ec -in private-key.pem -pubout -out public-key.pem
   ```
5. **Register the partner account** (one-time) by calling the Fleet API
   `/api/1/partner_accounts` with a partner token for your domain.
6. **Fleet Telemetry (recommended).** Configure the vehicle to stream telemetry
   to your Fleet Telemetry server, which normalizes and forwards points to this
   backend's `POST /api/telemetry/ingest`. This avoids frequent polling and is
   gentle on the vehicle's battery.
7. Fill the values into `.env` and restart. Set `USE_MOCK_DATA=false` to use
   real Tesla calls.

> The OAuth flow in `app/services/tesla_oauth.py` requests **only** the two
> read-only scopes above and falls back to clearly-labelled mock tokens when no
> client credentials are configured, so you can develop the whole flow offline.

## Architecture

```
Tesla Fleet Telemetry ──▶ POST /api/telemetry/ingest ──▶ location_points
                                                              │
                                              trip_reconstruction worker
                                                              │
                                                   trips + parking_events
                                                              │
                                       iOS app  ◀── trip / map-history APIs
```

## Trip detection (`app/services/trip_reconstruction.py`)

Pure, DB-free worker (unit-tested in `tests/test_trip_detection.py`):

- A trip is *in motion* when `speed_mph > 1` or `gear ∈ {D, R}`.
- A trip ends after the vehicle is stopped ≥ **5 minutes** (`speed == 0`,
  `gear` is `P`/null).
- Stops **< 5 min are merged** into the same trip; stops **> 10 min always
  split**.
- Movement **< 0.1 mile is ignored**.
- Distance uses the **odometer delta** when available, falling back to GPS path
  length.
- **Impossible GPS jumps** (implied speed > 200 mph) are filtered first.
- Routes are simplified with **Douglas–Peucker** and stored as both an encoded
  polyline and GeoJSON.
- A **parking event** spans each trip's end to the next trip's start.

## Database schema

`users`, `tesla_tokens` (encrypted), `vehicles`, `location_points`
(+ PostGIS `location geography(Point,4326)` generated column with a GIST index),
`trips`, `parking_events`, `privacy_zones`. See `app/models/` and the initial
migration `alembic/versions/0001_initial_schema.py`.

## API reference

### Auth
```
GET  /auth/tesla/start          → { authorize_url, state }
GET  /auth/tesla/callback       (OAuth redirect target)
POST /auth/logout
POST /auth/disconnect-tesla
```

### Vehicles
```
GET  /api/vehicles
GET  /api/vehicles/{vehicle_id}
POST /api/vehicles/{vehicle_id}/enable-tracking
POST /api/vehicles/{vehicle_id}/pause-tracking
POST /api/vehicles/{vehicle_id}/resume-tracking
```

### Telemetry (write path — read-only data only)
```
POST /api/telemetry/ingest      { vehicle_id|vin, points: [...] }
```

### Trips
```
GET    /api/vehicles/{vehicle_id}/trips?from=YYYY-MM-DD&to=YYYY-MM-DD
GET    /api/trips/{trip_id}
GET    /api/trips/{trip_id}/route
DELETE /api/trips/{trip_id}
```

### Map history & parking
```
GET /api/vehicles/{vehicle_id}/map-history?date=YYYY-MM-DD
GET /api/vehicles/{vehicle_id}/parking-events?from=YYYY-MM-DD&to=YYYY-MM-DD
```

### Privacy
```
POST   /api/privacy/export       (CSV download)
DELETE /api/privacy/delete-all
GET    /api/privacy/zones
POST   /api/privacy/zones
DELETE /api/privacy/zones/{zone_id}
```
