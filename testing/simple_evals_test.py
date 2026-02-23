#!/usr/bin/env python
"""
Simple direct test - no async complexity
Just test if data can be stored in evals table
"""
import sys
sys.path.insert(0, '..')

if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio

async def test():
    print("SIMPLE EVALS TABLE TEST")
    print("=" * 70)
    print()

    try:
        from app.backend.db.db import get_connection, DB_ENABLED

        print(f"1. DB_ENABLED: {DB_ENABLED}")

        if not DB_ENABLED:
            print("   ✗ Database not configured")
            return

        # Get connection
        conn = await get_connection()
        print(f"2. Connection: OK")

        # Check count
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) as cnt FROM evals")
            row = await cur.fetchone()
            print(f"3. Result type: {type(row)}")
            print(f"4. Result value: {row}")

            # Try different ways to access
            try:
                count = row['cnt']
                print(f"5. Access via ['cnt']: {count} ✓")
            except:
                try:
                    count = row[0]
                    print(f"5. Access via [0]: {count} ✓")
                except Exception as e:
                    print(f"5. Can't access result: {e}")
                    print(f"   Result attributes: {dir(row)}")

        await conn.close()
        print()
        print("Test completed!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())

