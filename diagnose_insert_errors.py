#!/usr/bin/env python
"""
Diagnose insert errors - test both evals and analysis_lines tables
"""
import asyncio
import sys
sys.path.insert(0, '.')

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    print("=" * 80)
    print("DIAGNOSING INSERT ERRORS")
    print("=" * 80)
    print()

    try:
        from app.backend.db.db import get_connection

        conn = await get_connection()
        print("[OK] Connected to database")
        print()

        async with conn.cursor() as cur:
            # Check both tables
            print("1. Current data in tables:")
            print("-" * 80)

            await cur.execute("SELECT COUNT(*) as cnt FROM evals;")
            evals_count = (await cur.fetchone())['cnt']

            await cur.execute("SELECT COUNT(*) as cnt FROM analysis_lines;")
            lines_count = (await cur.fetchone())['cnt']

            print(f"   evals table:          {evals_count} rows")
            print(f"   analysis_lines table: {lines_count} rows")
            print()

            # Check depth distribution
            if lines_count > 0:
                print("2. Depth distribution in analysis_lines:")
                print("-" * 80)

                await cur.execute("""
                    SELECT depth, COUNT(*) as cnt
                    FROM analysis_lines
                    GROUP BY depth
                    ORDER BY depth DESC;
                """)
                rows = await cur.fetchall()

                for row in rows:
                    print(f"   Depth {row['depth']:3d}: {row['cnt']:3d} lines")
                print()

                # Check for depth < 15 (should be 0)
                await cur.execute("SELECT COUNT(*) as cnt FROM analysis_lines WHERE depth < 15;")
                shallow = (await cur.fetchone())['cnt']

                if shallow > 0:
                    print(f"[WARNING] {shallow} lines with depth < 15 (should be 0!)")
                else:
                    print("[OK] No lines with depth < 15 (correct)")
                print()

            # Check if there are any partial/incomplete entries
            print("3. Checking for incomplete entries:")
            print("-" * 80)

            await cur.execute("""
                SELECT COUNT(*) as cnt
                FROM analysis_lines
                WHERE best_move IS NULL OR score_cp IS NULL;
            """)
            incomplete = (await cur.fetchone())['cnt']

            if incomplete > 0:
                print(f"[WARNING] {incomplete} lines missing best_move or score_cp")
            else:
                print("[OK] All entries have best_move and score_cp")
            print()

            # Show sample of recent data
            if lines_count > 0:
                print("4. Sample data (most recent):")
                print("-" * 80)

                await cur.execute("""
                    SELECT fen, depth, line_number, best_move, score_cp, updated_at
                    FROM analysis_lines
                    ORDER BY updated_at DESC, depth DESC
                    LIMIT 6;
                """)
                rows = await cur.fetchall()

                for i, row in enumerate(rows, 1):
                    fen_short = row['fen'][:30] + "..."
                    print(f"   {i}. Depth {row['depth']}, Line {row['line_number']}: {row['best_move']} ({row['score_cp']}cp)")
                print()

        await conn.close()

        print("=" * 80)
        if lines_count > 0:
            print("[YES] Analysis_lines table has data!")
            print("Check the sample above for any issues")
        else:
            print("[NO] Analysis_lines table is empty")
            print("Run backend and analyze a position to populate it")
        print("=" * 80)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

