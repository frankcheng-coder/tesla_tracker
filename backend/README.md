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

## Connect your own Tesla (real data)

> **Reality check:** Tesla's API has **no historical-trip endpoint**. You cannot
> import trips from before you connect. This app records data *going forward*:
> it polls your vehicle's current state and the reconstruction worker builds
> trips from those samples. So "trip history" = everything since you connected.

The quickest real path is **polling `vehicle_data`** (implemented in
`app/services/tesla_fleet.py` + `app/services/poller.py`), which avoids setting
up a Fleet Telemetry streaming server. Everything that needs a key from you is
marked `TODO(you)` in the code (`app/config.py`, `.env.example`, the OAuth/Fleet
services).

Steps:

1. Complete the **Tesla Developer setup** below (you need a public HTTPS domain
   to host the public key — this is the real hurdle for a personal test).
2. Fill `backend/.env` with the `TESLA_*` values and a stable
   `TOKEN_ENCRYPTION_KEY`, and set **`USE_MOCK_DATA=false`**.
3. Bring up the database and schema:
   ```bash
   docker compose up -d
   alembic upgrade head
   ```
4. Authorize your account: open `GET /auth/tesla/start`, visit the returned
   `authorize_url`, log in, and approve the **read-only** scopes. Tesla redirects
   to `/auth/tesla/callback`, which stores your encrypted tokens and syncs your
   vehicle list.
5. Enable tracking for your car:
   `POST /api/vehicles/{vehicle_id}/enable-tracking`.
6. Start the read-only poller:
   ```bash
   python -m app.poll --interval 60
   ```
   Drive around; trips and parking events appear via the normal trip APIs and in
   the iOS app (point it at the backend via `APIMode.live` in `AppEnvironment.swift`).

> The poller only ever **reads** `vehicle_data`. It never sends a command and
> never wakes the car (a wake call is not read-only) — if the car is asleep the
> poll is simply skipped. Use a longer interval while parked so the car can sleep
> and you don't drain its battery.

### Fastest official path (Cloudflare Tunnel) — step by step

This gets the official Fleet API working locally in ~10 minutes without owning a
domain. Cloudflare's free quick tunnel gives you a public HTTPS URL with **no
browser-warning page** (so Tesla can fetch your public key).

```bash
# 0) one-time: install the tunnel tool
brew install cloudflared

# 1) generate your Tesla key pair (served at the well-known URL automatically)
cd backend && source .venv/bin/activate
python -m app.tesla_setup genkey

# 2) start the backend
USE_MOCK_DATA=false uvicorn app.main:app --port 8000
#    (set DATABASE_URL + run `alembic upgrade head` first; `docker compose up -d`)

# 3) in another terminal, expose it publicly
cloudflared tunnel --url http://localhost:8000
#    -> prints a URL like https://random-words.trycloudflare.com
```

Now use that tunnel host as your domain:

4. **Create the Tesla Developer app** at <https://developer.tesla.com>:
   - **Allowed Origin / domain**: `random-words.trycloudflare.com`
   - **Redirect URI**: `https://random-words.trycloudflare.com/auth/tesla/callback`
   - **Scopes**: tick **`vehicle_device_data`** and **`vehicle_location`** only.
   - Copy the **Client ID** and **Client Secret**.

5. **Fill `backend/.env`** and restart the server:
   ```ini
   USE_MOCK_DATA=false
   TOKEN_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   TESLA_CLIENT_ID=...
   TESLA_CLIENT_SECRET=...
   TESLA_DEVELOPER_DOMAIN=random-words.trycloudflare.com
   TESLA_REDIRECT_URI=https://random-words.trycloudflare.com/auth/tesla/callback
   TESLA_AUDIENCE=https://fleet-api.prd.na.vn.cloud.tesla.com   # EU: ...prd.eu...
   ```

6. **Verify + register your domain** with Tesla (one-time):
   ```bash
   python -m app.tesla_setup check             # public key URL should say OK
   python -m app.tesla_setup register-partner  # registers the domain
   ```

7. **Authorize your account** (YOU log in on Tesla's page — the app never sees
   your password): open
   `https://random-words.trycloudflare.com/auth/tesla/start`, then visit the
   returned `authorize_url`, sign in, approve the read-only scopes. Tesla
   redirects to `/auth/tesla/callback`, which stores your encrypted tokens and
   syncs your vehicles.

8. **Enable tracking and start the read-only poller**:
   ```bash
   curl -X POST https://<tunnel>/api/vehicles/<vehicle_id>/enable-tracking
   python -m app.poll --interval 60
   ```
   Drive around; trips, routes, and parking appear in the trip APIs and the iOS
   app (set `APIMode.live(URL...)` in `AppEnvironment.swift`).

> ⚠️ Quick-tunnel caveats: the `trycloudflare.com` host **changes every time you
> restart** `cloudflared`, and you'd have to update the Tesla app + `.env` +
> re-register. For anything beyond a quick test, use a stable domain (a named
> Cloudflare tunnel, or your own).
>
> Endpoints/regions occasionally change — cross-check against the current
> [Tesla Fleet API docs](https://developer.tesla.com/docs/fleet-api) if a step
> returns an unexpected error.

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
