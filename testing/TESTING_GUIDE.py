#!/usr/bin/env python
"""
COMPLETE DEBUGGING & SOLUTION GUIDE

The evals table wasn't being populated due to:
1. Very short timeout (0.3s) causing Stockfish to not return analysis
2. Insufficient logging to see what was failing

FIXES APPLIED:
✓ Increased default time_limit from 0.3s to 1.0s
✓ Increased default depth from 18 to 15
✓ Added detailed logging to see what's happening
✓ Added better error reporting

NOW TO TEST:
"""

import sys
print(__doc__)

print("""
STEP 2: In Terminal 2, run tests
────────────────────────────────────────────────────────────────────
Run:
  cd <project-root>
  pytest testing/ -v

Expected: Backend starts on http://127.0.0.1:8000


STEP 2: In Terminal 2, test the /analyze endpoint
────────────────────────────────────────────────────────────────────
Run:
  cd C:\\Users\\dimon\\PycharmProjects\\chess_analyzer
  python manual_upload_test.py

This will:
  1. Upload a test PGN
  2. Trigger batch analysis
  3. Show detailed logs from backend (see Terminal 1)


STEP 3: Check database
────────────────────────────────────────────────────────────────────
Run:
  psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

Expected: Should show count > 0


WHAT TO LOOK FOR IN BACKEND LOGS:
────────────────────────────────────────────────────────────────────

When analysis starts, you should see:
  ✓ "Analyzing FEN (depth=15, time=1.0s, force=False)"
  ✓ "Cache miss or DB disabled, running Stockfish analysis..."
  ✓ "Starting Stockfish analysis: depth=15, time=1.0s"
  ✓ "Stockfish returned: 1 infos"
  ✓ "Analysis result: best_move=e2e4, score_cp=20, depth=15"
  ✓ "Storing evaluation to DB..."
  ✓ "Upserting eval: fen=... best_move=e2e4 score_cp=20 depth=15"
  ✓ "Upsert query executed"
  ✓ "Changes committed to DB"
  ✓ "Stored evaluation in DB for FEN"

If you see errors, they will be logged with details.


TROUBLESHOOTING:
────────────────────────────────────────────────────────────────────

If evals table is still empty after testing:

1. Check backend logs for errors
   - Look for "✗" or "ERROR" in output
   - Common issues: Stockfish not found, database connection error

2. Verify Stockfish works
   - Run: python test_stockfish_direct.py

3. Verify database connection
   - Run: python check_all_tables.py

4. Test /analyze endpoint directly
   - Run: python testing/test_analyze_stores_evals.py


NEXT STEPS:
────────────────────────────────────────────────────────────────────

Once evals table has data:

1. Upload a real PGN file via web UI (http://localhost:8000)
2. Watch progress in browser console (F12)
3. Check logs show analysis happening
4. Verify evals table populated
5. Navigate the game - should be instant <10ms per position!

""")

print("Ready to test? Follow the steps above!")

