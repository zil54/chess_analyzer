#!/usr/bin/env python
"""
CURRENT DATABASE UPDATE DEPTH SETTINGS

Answer to: "So on what depth is it now updating DB?"
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║              DATABASE UPDATE DEPTH SETTINGS - CURRENT              ║
╚════════════════════════════════════════════════════════════════════╝

SUMMARY:
────────────────────────────────────────────────────────────────────

When you upload a PGN and it auto-analyzes:
  → Depth: 15
  → Time limit: 1.0 second per position

When you manually call /analyze endpoint:
  → Depth: 20 (default)
  → Time limit: 0.5 seconds (default)


DETAILED BREAKDOWN:
────────────────────────────────────────────────────────────────────

1. AUTO-ANALYSIS (PGN Upload)
   ─────────────────────────────
   File: app/frontend/src/components/Analyzer.vue (line ~297)
   
   Configuration:
     depth: 15
     time_limit: 1.0 second
   
   Triggered: Automatically after PGN upload
   Storage: evals table with depth=15


2. MANUAL /analyze ENDPOINT
   ─────────────────────────────
   File: app/backend/api/routes.py (line ~507)
   
   Configuration (defaults):
     depth: 20 (if not specified in request)
     time_limit: 0.5 seconds (if not specified)
   
   Triggered: When called via POST /analyze
   Storage: evals table with depth=20 (or whatever specified)


3. TEST SCRIPTS
   ─────────────────────────────
   
   manual_upload_test.py (line ~40):
     depth: 10
     time_limit: 0.5 seconds
   
   test_analyze_stores_evals.py:
     depth: 10
     time_limit: 0.5 seconds


SETTINGS COMPARISON:
────────────────────────────────────────────────────────────────────

┌─────────────────────────┬────────┬──────────────┐
│ Source                  │ Depth  │ Time Limit   │
├─────────────────────────┼────────┼──────────────┤
│ PGN Auto-Analysis       │   15   │  1.0 sec     │
│ Manual /analyze (min)   │   20   │  0.5 sec     │
│ Test Script             │   10   │  0.5 sec     │
└─────────────────────────┴────────┴──────────────┘


ANALYSIS TIME IMPLICATIONS:
────────────────────────────────────────────────────────────────────

40-move game (80 positions):

Auto-Analysis (depth=15):
  80 positions × 1.0 sec = 80 seconds
  → evals table has 80 rows with depth=15

Manual /analyze (depth=20):
  Single position × 0.5 sec = 0.5 seconds
  → evals table updated with depth=20 (if ≥ 15)

Deeper Manual (depth=25):
  Single position × 1.5 sec = 1.5 seconds  
  → evals table updated with depth=25 (if > 15)


DEPTH PROGRESSION:
────────────────────────────────────────────────────────────────────

Typical workflow:

Step 1: Upload PGN (auto-analyze)
  → All positions stored with depth=15
  Database: [80 rows with depth=15]

Step 2: User wants deeper analysis (call /analyze with depth=25)
  → Each position re-analyzed
  → 25 >= 15? YES → Update to depth=25
  Database: [80 rows with depth=25]

Step 3: User wants even deeper (call /analyze with depth=30)
  → 30 >= 25? YES → Update to depth=30
  Database: [80 rows with depth=30]

Result: Evaluations improve over time! 📈


TO CHANGE THESE SETTINGS:
────────────────────────────────────────────────────────────────────

To increase auto-analysis depth:
  File: app/frontend/src/components/Analyzer.vue (line 297)
  Change:
    depth: 15,          → depth: 20,
    time_limit: 1.0     → time_limit: 2.0

To change manual /analyze defaults:
  File: app/backend/api/routes.py (line 507)
  Change:
    body.get("depth", 20)       → body.get("depth", 25)
    body.get("time_limit", 0.5) → body.get("time_limit", 1.0)


CURRENT CONFIGURATION IS:
────────────────────────────────────────────────────────────────────

✓ Auto-analysis: depth=15 (balanced: reasonable quality, not too slow)
✓ Manual analyze: depth=20 default (stronger than auto, for refinement)
✓ Can be overridden: Both accept custom depth in requests

This means:
  • PGN uploads get reasonable analysis (depth=15)
  • Manual deepening available (up to any depth)
  • Can incrementally improve as needed
  • Knowledge base grows as deeper analysis runs


RECOMMENDATION FOR PRODUCTION:
────────────────────────────────────────────────────────────────────

Current setup is good for:
  ✓ Fast batch analysis on upload (depth=15 reasonable)
  ✓ Manual refinement available (adjust depth as needed)
  ✓ Balanced speed vs quality

If you want:
  • Faster uploads: Reduce auto-depth to 12
  • Better auto-analysis: Increase to 20
  • Faster manual: Increase time_limit to 2.0 seconds
  • Better manual: Increase depth to 30


STATUS: ✅ CONFIGURED AND WORKING
────────────────────────────────────────────────────────────────────

Database is currently updating with:
  • depth=15 for auto-analysis (PGN uploads)
  • depth=20 for manual calls (default)
  • Depth-aware updates (never downgrades)

All evaluations stored with their depth for future comparison.
""")

print("\n" + "="*70)
print("SUMMARY: Database updates at depth=15 (auto) or depth=20 (manual)")
print("="*70)

