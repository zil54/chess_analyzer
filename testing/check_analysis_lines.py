#!/usr/bin/env python
"""
Check if analysis_lines table is being populated - NO psql required!
This uses Python/asyncio to connect directly to PostgreSQL
"""
import asyncio
import sys
sys.path.insert(0, '..')

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    print("=" * 80)
    print("CHECKING ANALYSIS_LINES TABLE")
    print("=" * 80)
    print()

    try:
        from app.backend.db.db import get_connection

        conn = await get_connection()
        print("✓ Connected to database")
        print()

        async with conn.cursor() as cur:
            # Check analysis_lines count
            print("Checking analysis_lines table:")
            await cur.execute("SELECT COUNT(*) as cnt FROM analysis_lines;")
            result = await cur.fetchone()
            count = result['cnt'] if result else 0
            print(f"  Total rows: {count}")
            print()

            # Check evals count
            print("Checking evals table:")
            await cur.execute("SELECT COUNT(*) as cnt FROM evals;")
            result = await cur.fetchone()
            evals_count = result['cnt'] if result else 0
            print(f"  Total rows: {evals_count}")
            print()

            if count == 0:
                print("⚠ analysis_lines table is EMPTY")
                print()
                print("The table exists but has no data yet.")
                print()
                print("To populate it:")
                print("  1. Start backend: python -m app.backend.main")
                print("  2. Open http://localhost:8000")
                print("  3. Click 'Analyze' on a position")
                print("  4. Wait until depth reaches 15+")
                print("  5. All 3 lines will be stored automatically")
                print()
                print("Then run this script again to verify!")
                return False
            else:
                print("✅ analysis_lines table HAS DATA!")
                print()

                # Show depth distribution
                print("Depth distribution:")
                await cur.execute("""
                    SELECT depth, COUNT(*) as cnt
                    FROM analysis_lines
                    GROUP BY depth
                    ORDER BY depth DESC
                    LIMIT 10;
                """)
                rows = await cur.fetchall()
                for row in rows:
                    print(f"  Depth {row['depth']:3d}: {row['cnt']:3d} lines")
                print()

                # Show line number distribution
                print("Line number distribution:")
                await cur.execute("""
                    SELECT line_number, COUNT(*) as cnt
                    FROM analysis_lines
                    GROUP BY line_number
                    ORDER BY line_number;
                """)
                rows = await cur.fetchall()
                for row in rows:
                    print(f"  Line {row['line_number']}: {row['cnt']} entries")
                print()

                # Show sample
                print("Sample data (latest):")
                await cur.execute("""
                    SELECT fen, depth, line_number, best_move, score_cp
                    FROM analysis_lines
                    ORDER BY depth DESC, line_number ASC
                    LIMIT 3;
                """)
                rows = await cur.fetchall()
                for i, row in enumerate(rows, 1):
                    fen_short = row['fen'][:40] + "..."
                    print(f"  {i}. Depth {row['depth']}, Line {row['line_number']}: {row['best_move']} ({row['score_cp']}cp)")
                print()

                return True

        await conn.close()

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

