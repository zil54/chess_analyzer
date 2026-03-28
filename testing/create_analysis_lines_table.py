#!/usr/bin/env python
"""
Create analysis_lines table in PostgreSQL
This script creates the analysis_lines table to store all 3 analysis lines per position at each depth
"""
import asyncio
import sys
sys.path.insert(0, '..')

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    print("=" * 80)
    print("CREATING analysis_lines TABLE")
    print("=" * 80)
    print()

    try:
        from app.backend.db.db import get_connection

        conn = await get_connection()
        print("✓ Connected to database")
        print()

        async with conn.cursor() as cur:
            # Create analysis_lines table
            print("Creating analysis_lines table...")
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS public.analysis_lines (
                    fen TEXT NOT NULL,
                    depth INT NOT NULL,
                    line_number INT NOT NULL,
                    best_move TEXT,
                    score_cp INT,
                    score_mate INT,
                    pv TEXT,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (fen, depth, line_number),
                    FOREIGN KEY (fen) REFERENCES public.evals(fen)
                );
            """)
            print("✓ analysis_lines table created")
            print()

            # Verify evals table exists
            print("Verifying evals table...")
            await cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name='evals'
                ) as exists;
            """)
            result = await cur.fetchone()
            evals_exists = result['exists'] if result else False
            print(f"✓ evals table exists: {evals_exists}")
            print()

            # Check evals table structure
            print("evals table structure:")
            await cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name='evals'
                ORDER BY ordinal_position;
            """)
            evals_cols = await cur.fetchall()
            for col in evals_cols:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"  ├─ {col['column_name']:15s} {col['data_type']:20s} {nullable}")
            print()

            # Check analysis_lines table structure
            print("analysis_lines table structure:")
            await cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name='analysis_lines'
                ORDER BY ordinal_position;
            """)
            lines_cols = await cur.fetchall()
            for col in lines_cols:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"  ├─ {col['column_name']:15s} {col['data_type']:20s} {nullable}")
            print()

            # Show indexes
            print("Indexes:")
            await cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename IN ('evals', 'analysis_lines');
            """)
            indexes = await cur.fetchall()
            for idx in indexes:
                print(f"  ├─ {idx['indexname']:30s} on {idx['indexdef'][:50]}...")
            print()

        await conn.commit()
        await conn.close()

        print("=" * 80)
        print("✅ SUCCESS - Tables ready!")
        print("=" * 80)
        print()
        print("Table Structure:")
        print()
        print("evals (unchanged):")
        print("  └─ Store best evaluation per FEN")
        print("     ├─ fen (PRIMARY KEY)")
        print("     ├─ best_move")
        print("     ├─ score_cp")
        print("     ├─ score_mate")
        print("     ├─ depth")
        print("     ├─ pv")
        print("     └─ created_at")
        print()
        print("analysis_lines (NEW):")
        print("  └─ Store all 3 lines per FEN at each depth")
        print("     ├─ fen (FK → evals.fen)")
        print("     ├─ depth")
        print("     ├─ line_number (1, 2, or 3)")
        print("     ├─ best_move")
        print("     ├─ score_cp")
        print("     ├─ score_mate")
        print("     ├─ pv")
        print("     └─ updated_at")
        print()

        return True

    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

