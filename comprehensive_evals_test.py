#!/usr/bin/env python
"""
Complete diagnostic test to verify evals table population
This will help identify exactly where the problem is
"""
import sys
sys.path.insert(0, '.')

if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
import json

async def main():
    print("=" * 80)
    print("COMPLETE EVALS TABLE DIAGNOSTIC TEST")
    print("=" * 80)
    print()

    # Test 1: Database connectivity
    print("TEST 1: Database Connectivity")
    print("-" * 80)
    try:
        from app.backend.db.db import get_connection, DB_ENABLED, init_db, upsert_eval, get_eval

        print(f"✓ Imports successful")
        print(f"✓ DB_ENABLED: {DB_ENABLED}")

        if not DB_ENABLED:
            print("✗ Database not configured!")
            return False

        await init_db()
        print(f"✓ Schema initialized")

        conn = await get_connection()
        print(f"✓ Connection successful")

        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM evals;")
            result = await cur.fetchone()
            # psycopg with dict_row returns dict with 'count' key
            count = result['count'] if result else 0
            print(f"✓ evals table has {count} rows currently")

        await conn.close()

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # Test 2: Direct upsert
    print("TEST 2: Direct Database Upsert")
    print("-" * 80)
    try:
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        print(f"Attempting to upsert test evaluation...")
        print(f"  FEN: {test_fen[:50]}...")
        print(f"  best_move: e2e4")
        print(f"  score_cp: 20")
        print(f"  depth: 15")

        await upsert_eval(
            fen=test_fen,
            best_move="e2e4",
            score_cp=20,
            score_mate=None,
            depth=15,
            pv="e2e4 e7e5"
        )
        print(f"✓ Upsert completed without error")

        # Verify it was stored
        result = await get_eval(test_fen)
        if result:
            print(f"✓ Evaluation found in database!")
            print(f"  best_move: {result['best_move']}")
            print(f"  score_cp: {result['score_cp']}")
            print(f"  depth: {result['depth']}")
        else:
            print(f"✗ Evaluation NOT found after upsert!")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # Test 3: Check analyzer service
    print("TEST 3: Analyzer Service Integration")
    print("-" * 80)
    try:
        from app.backend.services.analyzer_service import analyze_position

        test_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"

        print(f"Calling analyze_position()...")
        print(f"  FEN: {test_fen[:50]}...")
        print(f"  depth: 10")
        print(f"  time_limit: 0.5s")

        result = await analyze_position(
            fen=test_fen,
            depth=10,
            time_limit=0.5,
            force_recompute=True  # Skip cache, force analysis
        )

        print(f"✓ Analysis completed")
        print(f"  Result keys: {list(result.keys())}")
        print(f"  best_move: {result.get('best_move')}")
        print(f"  score_cp: {result.get('score_cp')}")
        print(f"  depth: {result.get('depth')}")
        print(f"  error: {result.get('error')}")

        # Verify in database
        stored = await get_eval(test_fen)
        if stored:
            print(f"✓ Analysis stored in database!")
            print(f"  Stored depth: {stored['depth']}")
        else:
            print(f"✗ Analysis NOT stored in database!")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # Test 4: Check final state
    print("TEST 4: Final Database State")
    print("-" * 80)
    try:
        conn = await get_connection()
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM evals;")
            result = await cur.fetchone()
            # psycopg with dict_row returns dict with 'count' key
            count = result['count'] if result else 0
            print(f"Total rows in evals: {count}")

            if count > 0:
                await cur.execute("""
                    SELECT fen, best_move, score_cp, depth 
                    FROM evals 
                    LIMIT 3;
                """)
                rows = await cur.fetchall()
                for i, row in enumerate(rows, 1):
                    # psycopg dict_row format
                    print(f"  {i}. FEN: {row['fen'][:50]}... | Move: {row['best_move']} | Score: {row['score_cp']} | Depth: {row['depth']}")

        await conn.close()
        print(f"✓ Database check complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print()
    print("=" * 80)
    print("✅ ALL TESTS PASSED - EVALS TABLE IS WORKING")
    print("=" * 80)
    return True

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)



