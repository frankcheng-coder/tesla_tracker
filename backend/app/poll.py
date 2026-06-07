"""Run the read-only Tesla poller in a loop.

Usage:
    python -m app.poll --interval 60

Prerequisites (see README "Connect your own Tesla"):
  1. Tesla Developer app configured and .env filled in.
  2. `alembic upgrade head` run against a real PostGIS database.
  3. You have authorized the account (so a TeslaToken row exists) and at least
     one vehicle has tracking enabled.

This script only READS vehicle_data. It never sends a command and never wakes
the vehicle.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.database import SessionLocal
from app.services import poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("poll")


async def _run(interval: int) -> None:
    log.info("Starting read-only Tesla poller (interval=%ss). Ctrl-C to stop.", interval)
    while True:
        db = SessionLocal()
        try:
            stored = await poller.poll_all_once(db)
            log.info("Polled. Stored %d new point(s).", stored)
        except Exception as exc:  # keep the loop alive on transient errors
            log.exception("Poll failed: %s", exc)
        finally:
            db.close()
        await asyncio.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Tesla telemetry poller")
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Seconds between polls (default 60). Use a longer interval while "
        "parked to let the car sleep and save battery.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.interval))
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == "__main__":
    main()
