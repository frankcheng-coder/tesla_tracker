"""Tesla read-only trip logger backend.

Read-only by design: this package never exposes or calls any Tesla vehicle
*command* endpoints (lock/unlock, climate, charging, honk, summon, etc.).
It only ingests telemetry, reconstructs trips, and serves trip history.
"""

__version__ = "0.1.0"
