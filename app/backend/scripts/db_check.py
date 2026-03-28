"""CLI to validate Postgres connectivity using the app's .env config.

Usage:
  python -m app.backend.scripts.db_check

Exit codes:
  0  success
  2  database misconfigured (.env missing)
  3  connection failed
"""

from __future__ import annotations

import asyncio
import sys


def _ensure_windows_selector_loop() -> None:
    # psycopg async is incompatible with ProactorEventLoop on Windows.
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _amain() -> int:
    print("db_check: starting", flush=True)

    try:
        from app.backend.db.db import DB_ENABLED, DATABASE_URL, check_connection, init_db
    except Exception as e:
        print(f"Failed to import database module: {e}", flush=True)
        return 3

    if not DB_ENABLED:
        print("Database is not configured.", flush=True)
        print("Set DATABASE_URL in .env (repo root or app/backend/) to enable DB features.", flush=True)
        return 2

    print("DB_ENABLED=True", flush=True)
    print(f"DATABASE_URL={DATABASE_URL}", flush=True)

    try:
        ok = await check_connection()
        if not ok:
            print("Connectivity check returned False", flush=True)
            return 3

        # Initialize schema so the app can run without manual SQL.
        await init_db()
        print("OK: connected and schema initialized", flush=True)
        return 0
    except Exception as e:
        print(f"FAILED: could not connect/init schema: {e}", flush=True)
        return 3


def main() -> None:
    _ensure_windows_selector_loop()
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
