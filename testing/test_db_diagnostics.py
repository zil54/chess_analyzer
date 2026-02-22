#!/usr/bin/env python
"""
Debug script to check evals table and database status
"""

import asyncio
import sys

async def main():
    try:
        from app.backend.db.db import get_connection, DB_ENABLED, init_db
        
        print("=" * 70)
        print("DATABASE DIAGNOSTIC TEST")
        print("=" * 70)
        print()
        
        print(f"DB_ENABLED: {DB_ENABLED}")
        
        if not DB_ENABLED:
            print("⚠ Database is NOT configured!")
            print("Set DATABASE_URL in .env to enable")
            return False
        
        print("✓ Database is configured")
        print()
        
        # Initialize schema
        print("Initializing database schema...")
        await init_db()
        print("✓ Schema initialized")
        print()
        
        # Connect and check
        print("Connecting to database...")
        conn = await get_connection()
        print("✓ Connected")
        print()
        
        async with conn.cursor() as cur:
            # Check tables exist
            print("Checking tables...")
            
            for table in ['games', 'moves', 'evals']:
                await cur.execute(f"""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name='{table}'
                    );
                """)
                result = await cur.fetchone()
                exists = result[0] if result else False
                status = "✓" if exists else "✗"
                print(f"  {status} {table} table: {exists}")
            
            print()
            
            # Count rows in each table
            print("Counting rows in tables...")
            for table in ['games', 'moves', 'evals']:
                await cur.execute(f"SELECT COUNT(*) FROM {table};")
                result = await cur.fetchone()
                count = result[0] if result else 0
                print(f"  {table}: {count} rows")
            
            print()
            
            # Show sample evals if any exist
            print("Sample evaluations (first 3):")
            await cur.execute("""
                SELECT fen, best_move, score_cp, depth 
                FROM evals 
                LIMIT 3;
            """)
            rows = await cur.fetchall()
            
            if rows:
                for i, row in enumerate(rows, 1):
                    print(f"  {i}. FEN: {row[0][:50]}...")
                    print(f"     Best: {row[1]}, Score: {row[2]}, Depth: {row[3]}")
            else:
                print("  (No evaluations found)")
        
        await conn.close()
        
        print()
        print("=" * 70)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)

