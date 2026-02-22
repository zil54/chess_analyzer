#!/usr/bin/env python
"""
Test if games and moves tables are being updated when PGN is uploaded
"""
import sys
sys.path.insert(0, '.')

if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio

async def main():
    print("=" * 70)
    print("CHECKING ALL DB TABLES")
    print("=" * 70)
    print()

    try:
        from app.backend.db.db import get_connection, init_db

        # Initialize schema
        print("Initializing schema...")
        await init_db()
        print("✓ Schema initialized")
        print()

        # Check all tables
        conn = await get_connection()
        async with conn.cursor() as cur:
            for table in ['games', 'moves', 'evals']:
                await cur.execute(f"SELECT COUNT(*) FROM {table};")
                result = await cur.fetchone()
                count = result[0] if result else 0
                print(f"{table:10s}: {count:5d} rows")
        await conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())

