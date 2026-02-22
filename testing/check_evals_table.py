#!/usr/bin/env python
"""
Test evals table - with proper Windows event loop handling
"""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_db():
    """Test database and check evals table"""
    print("=" * 70)
    print("CHECKING EVALS TABLE")
    print("=" * 70)
    print()

    try:
        from app.backend.db.db import get_connection, DB_ENABLED, init_db

        print(f"✓ DB_ENABLED: {DB_ENABLED}")

        if not DB_ENABLED:
            print("✗ Database NOT configured!")
            return False

        # Initialize schema
        print("✓ Initializing database schema...")
        await init_db()
        print("✓ Schema initialized")

        # Connect
        print("✓ Connecting to database...")
        conn = await get_connection()
        print("✓ Connected!")
        print()

        async with conn.cursor() as cur:
            # Check evals count
            print("Checking evals table...")
            await cur.execute("SELECT COUNT(*) FROM evals;")
            result = await cur.fetchone()
            count = result[0] if result else 0
            print(f"  evals table has: {count} rows")
            print()

            if count > 0:
                print("✓ Evals table is populated!")
                print()
                print("Sample evaluations:")
                await cur.execute("""
                    SELECT fen, best_move, score_cp, depth 
                    FROM evals 
                    LIMIT 5;
                """)
                rows = await cur.fetchall()
                for i, row in enumerate(rows, 1):
                    print(f"  {i}. FEN: {row[0][:50]}...")
                    print(f"     Best: {row[1]}, Score: {row[2]}, Depth: {row[3]}")
            else:
                print("⚠ Evals table is EMPTY")
                print()
                print("Next steps to populate:")
                print("  1. Start backend: python -m app.backend.main")
                print("  2. Upload a PGN file via the web UI")
                print("  3. Wait for auto-analysis to complete")
                print("  4. Check browser console (F12) for status")
                print()
                print("Or test manually:")
                print("  python testing/test_analyze_stores_evals.py")
                print()
                print("OR use curl to test /analyze endpoint:")
                print("""
  curl -X POST http://localhost:8000/analyze \\
    -H "Content-Type: application/json" \\
    -d '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}'
                """)

        await conn.close()
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

asyncio.run(test_db())


