#!/usr/bin/env python
"""
EVALS TABLE STORAGE STRATEGY - FINAL DESIGN

Schema: Single evals table with depth-aware updates
Strategy: Keep only the best (deepest) evaluation per FEN
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║         EVALS TABLE STORAGE STRATEGY - CONFIRMED                   ║
╚════════════════════════════════════════════════════════════════════╝

TABLE SCHEMA:
────────────────────────────────────────────────────────────────────
evals (PRIMARY KEY: fen)
├── fen TEXT PRIMARY KEY
├── best_move TEXT
├── score_cp INT
├── score_mate INT
├── depth INT
├── pv TEXT
└── created_at TIMESTAMP


STORAGE STRATEGY: DEPTH-AWARE UPDATES
────────────────────────────────────────────────────────────────────

Keep only ONE evaluation per FEN:
- Always store the DEEPEST analysis available
- Never keep multiple depths for same position
- Always replace shallower with deeper

Example:
  FEN: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
  
  Step 1: Analyze with depth=20
    → Store: depth=20, best_move=e2e4, score_cp=20
  
  Step 2: Analyze with depth=46
    → 46 >= 20? YES → Replace completely
    → Store: depth=46, best_move=e2e4, score_cp=22
  
  Step 3: Analyze with depth=15
    → 15 >= 46? NO → Skip
    → Keep: depth=46, best_move=e2e4, score_cp=22
  
  Final state: One row with depth=46 (best)


QUERY BEHAVIOR:
────────────────────────────────────────────────────────────────────

SELECT * FROM evals WHERE fen = ?
→ Returns the deepest analysis for that position
→ Always current best evaluation
→ No history to manage


INSERTION/UPDATE LOGIC:
────────────────────────────────────────────────────────────────────

For each analysis:
  1. Check if FEN exists
  2. If exists:
     - If new_depth < existing_depth: SKIP
     - If new_depth >= existing_depth: UPDATE
  3. If not exists: INSERT


ADVANTAGES:
────────────────────────────────────────────────────────────────────

✓ Simple schema (no history table needed)
✓ Clean queries (always get best eval)
✓ No data bloat (not storing all attempts)
✓ Automatic improvement (deeper replaces shallower)
✓ Easy to maintain


DISADVANTAGES:
────────────────────────────────────────────────────────────────────

✗ No history (can't see how eval changed with depth)
✗ Can't track improvement over time (when was it improved)
✗ No visibility into analysis progression


USE CASES THIS SUPPORTS:
────────────────────────────────────────────────────────────────────

1. PGN Upload → Auto-analyze all at depth=20
   → evals table: all positions with depth=20

2. User asks for deeper: Analyze same game at depth=46
   → evals table: all positions updated to depth=46
   → Old depth=20 entries completely replaced

3. Different positions from different games
   → First game: positions A,B,C at depth=20
   → Second game: positions A,B,D at depth=20
   → Position E only in second game: stored at depth=20
   → If any position re-analyzed at higher depth: updated

4. Playing/analyzing live
   → Each position gets best available evaluation
   → If user deepens search: evaluation improves
   → Always shows best analysis


TYPICAL WORKFLOW:
────────────────────────────────────────────────────────────────────

1. Upload PGN → Auto-analyze all positions
   Database state: All FENs with depth=20

2. Navigate game → Get evals from evals table
   Result: Instant <10ms lookups, consistent depth

3. User wants deeper → Analyze with depth=46
   Database state: All FENs with depth=46

4. Upload another game with overlapping openings
   Database state: 
     - Shared opening positions: depth=46
     - New middle-game positions: depth=20
   (Auto-analysis uses depth=20, shared positions kept at higher depth)

5. Deepen analysis for entire second game
   Database state: All positions now at depth=46


EXAMPLE QUERIES:
────────────────────────────────────────────────────────────────────

Get evaluation for position:
  SELECT * FROM evals WHERE fen = ?
  → Returns: best_move, score_cp, depth (current best)

Get all depths in table:
  SELECT DISTINCT depth FROM evals ORDER BY depth DESC
  → Shows: [46, 25, 20] (evolution of deepest analyses)

Get positions at specific depth:
  SELECT COUNT(*) FROM evals WHERE depth = 46
  → Count of positions analyzed at depth 46

Monitor depth progression:
  SELECT depth, COUNT(*) FROM evals GROUP BY depth
  → Shows distribution of analysis depths


SUMMARY:
────────────────────────────────────────────────────────────────────

✓ Single evals table (no history needed)
✓ One evaluation per FEN (always deepest)
✓ Automatic depth-aware updates
✓ Simple, clean, efficient
✓ Works perfectly for chess analysis use case


STATUS: ✅ CONFIRMED AND DOCUMENTED
────────────────────────────────────────────────────────────────────

Schema: Fixed
Strategy: Keep best evaluation per FEN
Implementation: Depth-aware upsert
History: Not tracked (by design)

This approach is simple, efficient, and perfect for a chess analyzer!
""")

