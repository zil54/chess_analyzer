#!/usr/bin/env python
"""
Direct test to verify database connectivity and storage
"""
import sys
sys.path.insert(0, '.')

if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

async def main():
    print("=" * 70)
    print("DATABASE STORAGE TEST")
    print("=" * 70)
    print()

    # Check env
    db_url = os.getenv('DATABASE_URL')
    print(f"DATABASE_URL configured: {bool(db_url)}")
    if db_url:
        print(f"  URL: {db_url[:60]}...")
    print()

    try:
        from app.backend.db.db import get_connection, upsert_eval, get_eval, init_db

        print("✓ Imports successful")
        print()

        # Initialize schema
        print("Initializing database schema...")
        await init_db()
        print("✓ Schema initialized")
        print()

        # Test FEN
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        # Insert test data
        print(f"Inserting test evaluation...")
        print(f"  FEN: {test_fen[:50]}...")
        print(f"  best_move: e2e4")
        print(f"  score_cp: 20")
        print(f"  depth: 12")

        await upsert_eval(
            fen=test_fen,
            best_move="e2e4",
            score_cp=20,
            score_mate=None,
            depth=12,
            pv="e2e4 e7e5"
        )
        print("✓ Insert completed")
        print()

        # Verify by reading back
        print("Verifying data was stored...")
        result = await get_eval(test_fen)

        if result:
            print("✓ DATA FOUND IN DATABASE!")
            print(f"  FEN: {result['fen'][:50]}...")
            print(f"  best_move: {result['best_move']}")
            print(f"  score_cp: {result['score_cp']}")
            print(f"  depth: {result['depth']}")
            print(f"  created_at: {result['created_at']}")
        else:
            print("✗ NO DATA FOUND!")
            print("  This means upsert_eval is not working")

        print()

        # Count all evals
        conn = await get_connection()
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM evals;")
            count_result = await cur.fetchone()
            count = count_result[0] if count_result else 0
            print(f"Total evals in table: {count}")
        await conn.close()

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("Starting test...\n")
asyncio.run(main())
print()
print("=" * 70)

