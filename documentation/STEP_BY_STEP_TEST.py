#!/usr/bin/env python
"""
STEP-BY-STEP GUIDE TO POPULATE EVALS TABLE
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║        STEP-BY-STEP: HOW TO POPULATE EVALS TABLE                  ║
╚════════════════════════════════════════════════════════════════════╝

CHANGES MADE:
────────────────────────────────────────────────────────────────────
✓ Depth changed to 15 (as requested)
✓ Old /analyze endpoint removed from main.py
✓ New /analyze endpoint in routes.py is properly registered


FOLLOW THESE STEPS EXACTLY:
════════════════════════════════════════════════════════════════════

STEP 1: CLEAR DATABASE (optional, but recommended for testing)
────────────────────────────────────────────────────────────────────
Run in terminal:

  psql -U postgres -d chess_analyzer -c "DELETE FROM evals;"
  psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

Should show: count | 0


STEP 2: START BACKEND
────────────────────────────────────────────────────────────────────
Open Terminal 1 and run:

  cd <project-root>
  python -m app.backend.main

Wait for message:
  INFO:     Uvicorn running on http://127.0.0.1:8000

Keep this terminal open!


STEP 3: RUN DIAGNOSTIC TEST
────────────────────────────────────────────────────────────────────
Open Terminal 2 and run:

  cd <project-root>
  python comprehensive_evals_test.py

This will:
  1. Test database connectivity
  2. Test direct upsert to evals
  3. Test analyzer service with Stockfish
  4. Verify data is stored

You should see:
  ✓ All tests passing
  ✓ evals table populated

If this fails, it will tell you exactly where the problem is.


STEP 4: CHECK DATABASE
────────────────────────────────────────────────────────────────────
Open Terminal 3 and run:

  psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

Should show: count | > 0 (not 0!)


STEP 5: UPLOAD A PGN FILE (web UI)
────────────────────────────────────────────────────────────────────
1. Open browser: http://localhost:8000
2. Click "Upload PGN"
3. Select a PGN file (even small 5-move games work)
4. Wait for upload to complete
5. Watch backend terminal (Terminal 1) for messages

You should see:
  ✓ "Starting batch analysis of all positions..."
  ✓ "Batch analysis complete"
  ✓ Analysis logs showing what's happening

Then check database again:
  psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

Should have MORE rows!


EXPECTED TIMELINE:
════════════════════════════════════════════════════════════════════

For a 20-move (40-position) game at depth=15:

  Upload PGN:                    ~1 second
  Auto-analyze all positions:   ~40-60 seconds (1s per position × depth=15)
  Total:                         ~41-61 seconds
  
  Result: 40 rows in evals table @ depth=15


WHAT TO LOOK FOR IN BACKEND LOGS:
════════════════════════════════════════════════════════════════════

SUCCESS - You'll see:
  ✓ "Analyzing FEN (depth=15, time=1.0s)"
  ✓ "Starting Stockfish analysis"
  ✓ "Stockfish returned: 1 infos"
  ✓ "Analysis result: best_move=... score_cp=..."
  ✓ "Storing evaluation to DB..."
  ✓ "Upserting eval: fen=..."
  ✓ "Upsert query executed"
  ✓ "Changes committed to DB"

FAILURE - You'll see:
  ✗ "ERROR"
  ✗ "Exception"
  ✗ "No analysis returned"

If you see errors, copy them to terminal output.


TROUBLESHOOTING IF NOTHING IS STORED:
════════════════════════════════════════════════════════════════════

1. Check backend logs for errors (Terminal 1)
   Look for ✗ or ERROR

2. Check Stockfish exists:
   ls app/engine/sf.exe
   (should exist)

3. Check database connectivity:
   psql -U postgres -d chess_analyzer -c "\\dt"
   (should show tables: games, moves, evals)

4. Test analyzer service directly:
   python comprehensive_evals_test.py
   (will tell you exact problem)

5. Check .env has DATABASE_URL:
   cat .env
   (should show postgresql://...)


FINAL VERIFICATION:
════════════════════════════════════════════════════════════════════

After testing, verify everything works:

✓ Run: python comprehensive_evals_test.py
  → Should pass all 4 tests

✓ Run: psql -c "SELECT COUNT(*) FROM evals;"
  → Should show count > 0

✓ Run: psql -c "SELECT depth, COUNT(*) FROM evals GROUP BY depth;"
  → Should show distribution of depths

✓ Upload PGN via UI
  → Should see auto-analysis in logs
  → Should see evals table grow


If ALL of these work, your evals table is properly populated! 🎉
""")

