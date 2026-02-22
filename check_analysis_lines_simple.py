#!/usr/bin/env python
"""
Check analysis_lines - output to file so we can see results
"""
import asyncio
import sys
sys.path.insert(0, '.')

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    output = []
    output.append("=" * 80)
    output.append("ANALYSIS_LINES TABLE CHECK")
    output.append("=" * 80)
    output.append("")

    try:
        from app.backend.db.db import get_connection

        conn = await get_connection()
        output.append("[OK] Connected to database")
        output.append("")

        async with conn.cursor() as cur:
            # Check analysis_lines
            await cur.execute("SELECT COUNT(*) as cnt FROM analysis_lines;")
            result = await cur.fetchone()
            count = result['cnt'] if result else 0

            output.append(f"analysis_lines table: {count} rows")
            output.append("")

            if count > 0:
                output.append("[YES] TABLE IS POPULATED!")
                output.append("")

                # Show distribution
                await cur.execute("""
                    SELECT depth, COUNT(*) as cnt
                    FROM analysis_lines
                    GROUP BY depth
                    ORDER BY depth DESC;
                """)
                rows = await cur.fetchall()
                output.append("Depth distribution:")
                for row in rows:
                    output.append(f"  Depth {row['depth']}: {row['cnt']} lines")
                output.append("")

                # Show sample
                await cur.execute("""
                    SELECT depth, line_number, best_move, score_cp
                    FROM analysis_lines
                    ORDER BY depth DESC, line_number ASC
                    LIMIT 3;
                """)
                rows = await cur.fetchall()
                output.append("Sample data:")
                for row in rows:
                    output.append(f"  Depth {row['depth']}, Line {row['line_number']}: {row['best_move']} ({row['score_cp']}cp)")
            else:
                output.append("[NO] TABLE IS EMPTY")
                output.append("")
                output.append("To populate:")
                output.append("  1. python -m app.backend.main")
                output.append("  2. Open http://localhost:8000")
                output.append("  3. Click 'Analyze'")
                output.append("  4. Wait for depth >= 15")

        await conn.close()

    except Exception as e:
        output.append(f"[ERROR] {e}")
        import traceback
        output.append(traceback.format_exc())

    # Write to file
    with open('analysis_lines_check.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    # Print to console
    print('\n'.join(output))

if __name__ == "__main__":
    asyncio.run(main())






