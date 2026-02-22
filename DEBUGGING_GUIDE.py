#!/usr/bin/env python
"""
Complete debugging guide for evals table issue
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║           DEBUGGING: WHY NO DATA IN EVALS TABLE                  ║
╚════════════════════════════════════════════════════════════════════╝

STEP 1: Start the backend in one terminal
────────────────────────────────────────────────────────────────────
Run:
  cd C:\\Users\\dimon\\PycharmProjects\\chess_analyzer
  python -m app.backend.main

Expected output:
  INFO:     Started server process
  INFO:     Application startup complete
  INFO:     Uvicorn running on http://127.0.0.1:8000

STEP 2: In another terminal, run this script
────────────────────────────────────────────────────────────────────
Run:
  cd C:\\Users\\dimon\\PycharmProjects\\chess_analyzer
  python testing/test_analyze_stores_evals.py

STEP 3: Check database directly
────────────────────────────────────────────────────────────────────
Run:
  psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

Expected:
  Should show count > 0 if /analyze was called

POSSIBLE ISSUES:
────────────────────────────────────────────────────────────────────

1. Backend not running
   → Check if server is listening on port 8000
   → Run: netstat -an | findstr :8000

2. Database not configured
   → Check .env file has DATABASE_URL
   → Should be: postgresql://postgres:YUG0slavia@localhost:5432/chess_analyzer

3. PGN upload not triggering analysis
   → Check browser console (F12) for errors
   → Should see: "Starting batch analysis of all positions..."

4. /analyze endpoint not storing to DB
   → Test directly:
      curl -X POST http://localhost:8000/analyze \\
        -H "Content-Type: application/json" \\
        -d '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}'

   → Should return evaluation with cached=false initially

5. Stockfish not found
   → Check: app/engine/sf.exe exists
   → Download from: https://stockfishchess.org/download/

6. Analysis takes too long
   → Default depth=18, time=0.3s
   → Increase time_limit in batch analysis

TROUBLESHOOTING STEPS:
────────────────────────────────────────────────────────────────────
""")

import asyncio
import sys

async def test_db():
    """Test database connectivity"""
    print("\n[TEST 1] DATABASE CONNECTIVITY")
    print("─" * 70)
    
    try:
        from app.backend.db.db import get_connection, DB_ENABLED
        
        print(f"DB_ENABLED: {DB_ENABLED}")
        
        if not DB_ENABLED:
            print("✗ Database NOT configured!")
            print("  Set DATABASE_URL in .env")
            return False
        
        print("✓ Database is configured")
        
        conn = await get_connection()
        print("✓ Connection successful")
        
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM evals;")
            result = await cur.fetchone()
            count = result[0] if result else 0
            print(f"✓ evals table has {count} rows")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

async def main():
    result = await test_db()
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    print("\nRunning diagnostics...\n")
    asyncio.run(main())

