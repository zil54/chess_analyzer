#!/usr/bin/env python
"""
DEPTH-BASED EVAL UPDATES - Design Explanation

Question: Should evals be updated when depth hits certain #?
Answer: YES, but ONLY if new depth >= existing depth

This prevents accidentally overwriting better analyses with shallower ones.
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║          EVALUATION STORAGE STRATEGY - DEPTH AWARE                 ║
╚════════════════════════════════════════════════════════════════════╝

PROBLEM: 
────────────────────────────────────────────────────────────────────
Before this fix, the evals table would always overwrite regardless 
of depth:

  Timeline:
  ─────────────────────────────────────
  1. Analyze position with depth=20
     → Store: depth=20, best_move=e2e4, score_cp=20
  
  2. Later, analyze same position with depth=5
     → OVERWRITES: depth=5, best_move=d2d4, score_cp=15  ✗ WRONG!
  
  Result: Lost better analysis!


SOLUTION:
────────────────────────────────────────────────────────────────────
Now, only update if new depth >= existing depth:

  Timeline:
  ─────────────────────────────────────
  1. Analyze position with depth=20
     → Store: depth=20, best_move=e2e4, score_cp=20
  
  2. Later, analyze same position with depth=5
     → SKIP (5 < 20, shallower)
     → Keep: depth=20, best_move=e2e4, score_cp=20  ✓ CORRECT!
  
  3. Later, analyze same position with depth=25
     → UPDATE (25 >= 20, deeper)
     → Store: depth=25, best_move=e2e4, score_cp=22  ✓ BETTER!


BEHAVIOR:
────────────────────────────────────────────────────────────────────

Case 1: FEN doesn't exist
  → Always insert (first time seeing it)

Case 2: FEN exists with depth=15, new analysis is depth=10
  → SKIP - don't overwrite with shallower
  → Keep depth=15 evaluation

Case 3: FEN exists with depth=15, new analysis is depth=15
  → UPDATE - same depth, refresh the data
  → Update best_move, score_cp, pv, timestamp

Case 4: FEN exists with depth=15, new analysis is depth=20
  → UPDATE - new analysis is deeper
  → Store better analysis with depth=20


DATABASE LOGIC:
────────────────────────────────────────────────────────────────────

BEFORE (Wrong):
  INSERT INTO evals (...) VALUES (...)
  ON CONFLICT (fen) DO UPDATE SET
    best_move = EXCLUDED.best_move,
    score_cp = EXCLUDED.score_cp,
    depth = EXCLUDED.depth,
    ...

AFTER (Correct):
  1. Check if FEN exists: SELECT depth WHERE fen = ?
  2. If exists:
     - If new_depth < existing_depth: SKIP (don't update)
     - If new_depth >= existing_depth: UPDATE
  3. If not exists: INSERT


LOGGING:
────────────────────────────────────────────────────────────────────

You'll see in backend logs:

When skipping shallow update:
  ✓ Skipping update: new depth 10 < existing depth 15

When updating with deeper analysis:
  ✓ Updating eval: new depth 25 >= existing 15

When storing new FEN:
  ✓ Upsert query executed
  ✓ Changes committed to DB


PRACTICAL EXAMPLES:
────────────────────────────────────────────────────────────────────

Example 1: Batch analysis finds good moves
  1. Upload 40-move PGN
  2. Batch analyze all positions with depth=15, time=1.0s
  3. All 80 unique FENs stored with depth=15
  4. Later, user manually deepens analysis to depth=25
  5. Store depth=25 evaluations (better than 15)
  ✓ Each position improved as analysis deepens

Example 2: Multiple games with same openings
  1. Upload Game 1 (Italian Game)
  2. Analyze with depth=15
  3. Upload Game 2 (same Italian opening)
  4. Auto-analyze with depth=15
  5. Early positions already cached, skip (same depth)
  6. New positions from Game 2 stored
  ✓ Efficient: don't re-analyze, but track new positions

Example 3: Re-analyzing old games with better settings
  1. Old evaluation: depth=10, score=+0.5
  2. New analysis: depth=25, score=+0.3
  3. Better analysis replaces shallow one
  ✓ Knowledge base improves over time


BENEFITS:
────────────────────────────────────────────────────────────────────

✓ Never lose good analysis to shallow re-analysis
✓ Evaluations improve as deeper analysis becomes available
✓ Efficient: don't re-compute same depths
✓ Timestamp updated: can track when eval last improved
✓ Transparent: logs show what's happening


FILES CHANGED:
────────────────────────────────────────────────────────────────────

app/backend/db/db.py - upsert_eval() function:
  • Added depth comparison logic
  • Only updates if new_depth >= existing_depth
  • Logs when skipping shallow updates
  • Logs when performing deeper updates


TESTING:
────────────────────────────────────────────────────────────────────

To verify this works:

1. Upload PGN, analyze with depth=15
   → evals table has all FENs with depth=15

2. Manually trigger deeper analysis (depth=25)
   → Backend logs show:
     - Some: "Skipping update: new depth 25 >= existing 15" (first time)
     - Then: "Updating eval: new depth 25 >= existing 15" (on update)

3. Check database:
   psql -c "SELECT COUNT(DISTINCT depth) FROM evals;"
   → Should show: 2 (both depth=15 and depth=25)
   
   Or to see the progression:
   psql -c "SELECT depth, COUNT(*) FROM evals GROUP BY depth;"
   → Shows how many at each depth


EDGE CASES HANDLED:
────────────────────────────────────────────────────────────────────

✓ Null depths: Allows NULL depth (stores result regardless)
✓ First insert: New FENs always stored
✓ Same depth: Allows updates at same depth (refresh timestamp)
✓ Deeper: Always accepts deeper analysis
✓ Shallower: Always rejects shallower analysis
✓ Errors: Logs any issues, doesn't silently fail


SUMMARY:
────────────────────────────────────────────────────────────────────

Q: Should evals be updated when depth hits certain #?
A: YES - but only if it's EQUAL or DEEPER than existing

This ensures:
  • Better analyses always replace worse ones
  • Shallow analyses never overwrite good ones
  • Knowledge base continuously improves
  • Historical tracking via depth column
  • Efficient reuse of already-analyzed positions

Implementation: ✅ COMPLETE
""")

