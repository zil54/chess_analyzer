# Chess Analyzer - Visual Architecture Guide

## App Structure WITHOUT Database

```
┌─────────────────────────────────────────────┐
│         CHESS ANALYZER APPLICATION          │
├─────────────────────────────────────────────┤
│                                             │
│   Frontend (Vue.js)                         │
│   ├─ Board Display                      ✅  │
│   ├─ FEN Input                          ✅  │
│   ├─ Analysis Display                   ✅  │
│   └─ Board Navigation                   ✅  │
│                                             │
│   Backend (FastAPI)                        │
│   ├─ SVG Rendering    (POST /svg)       ✅  │
│   ├─ Live Analysis    (WS /ws/analyze)  ✅  │
│   ├─ PGN Upload       (POST /analyze)   ⚠️  │
│   │                   (parsed, not saved)   │
│   └─ Game Retrieval   (GET /games)      ❌  │
│       (needs database)                      │
│                                             │
│   Chess Engine (Stockfish)                 │
│   └─ Real-time Analysis              ✅      │
│                                             │
│   Database Connection                       │
│   └─ PostgreSQL                        ❌   │
│       (not configured, optional)            │
│                                             │
└─────────────────────────────────────────────┘

Legend:
✅ = Works without database
❌ = Requires database
⚠️ = Partial functionality
```

---

## Feature Availability Matrix

```
                WITHOUT DB    WITH DB
─────────────────────────────────────
Frontend          ✅            ✅
Board Render      ✅            ✅
Live Analysis     ✅            ✅
FEN Input         ✅            ✅
PGN Parsing       ✅            ✅
─────────────────────────────────────
PGN Storage       ❌            ✅
Game Library      ❌            ✅
Session Track     ❌            ✅
Eval Cache        ❌            ✅
Move History      ❌            ✅
─────────────────────────────────────
```

---

## Data Flow - WITHOUT Database

```
User Input (FEN)
       ↓
   Frontend
       ↓
  [POST /svg]
       ↓
   Backend
       ↓
  Stockfish
       ↓
   Analysis
       ↓
 [WS /ws/analyze]
       ↓
   Frontend
       ↓
Display Results
```

**Database:** Not involved ✅

---

## Data Flow - WITH Database (PGN Upload)

```
User Uploads PGN
       ↓
   Frontend
       ↓
 [POST /analyze_pgn]
       ↓
   Backend
       ↓
   Parse PGN ──→ Create Moves
       ↓              ↓
   Database      Stockfish
       ↓              ↓
 games table    analysis
 moves table
       ↓
Display + Store
```

**Database:** Required for storage ✅

---

## Endpoint Dependency Chart

```
┌─────────────────────────────────────┐
│      Endpoints Needing Database      │
├─────────────────────────────────────┤
│                                     │
│  POST /games                        │
│  GET /games                         │
│  GET /games/{id}/moves              │
│  GET /evals                         │
│  POST /analyze_pgn (persist part)   │
│                                     │
│  Status if DB missing:              │
│  Returns 503 Service Unavailable    │
│                                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│    Endpoints Working Without DB     │
├─────────────────────────────────────┤
│                                     │
│  GET /                              │
│  POST /svg                          │
│  WS /ws/analyze                     │
│  GET /health/db                     │
│                                     │
│  Status if DB missing:              │
│  Still works normally ✅             │
│                                     │
└─────────────────────────────────────┘
```

---

## Setup Comparison

### Setup A: Minimal (No Database)

```
Step 1: No configuration needed
Step 2: Run: python main.py
Step 3: Open: http://localhost:8000

Result:
✅ Board rendering works
✅ Live analysis works
✅ Frontend loads
❌ PGN persistence fails (as expected)

Use Case: Analysis tool, development, testing
```

### Setup B: Full (With Database)

```
Step 1: Install PostgreSQL
Step 2: Create chess_analyzer database
Step 3: Set DATABASE_URL in .env
Step 4: Run: python main.py

Result:
✅ Board rendering works
✅ Live analysis works
✅ Frontend loads
✅ PGN persistence works
✅ Game library works

Use Case: Production, game storage, library
```

---

## Database vs No-Database Timeline

```
START APP (No DATABASE_URL set)
│
├─ Startup:    ⚠️  Warning message (not an error)
│
├─ Board render:    ✅ Works immediately
│
├─ Analysis:        ✅ Works immediately
│
├─ PGN upload:      ⚠️  Parses but doesn't save
│
├─ Game list:       ❌ Returns 503 (expected)
│
└─ Result:         ✅ Core features work perfectly


ADD DATABASE (Set DATABASE_URL)
│
├─ Restart app:     ✅ All endpoints now work
│
├─ Board render:    ✅ Still works
│
├─ Analysis:        ✅ Still works
│
├─ PGN upload:      ✅ Now persists to DB
│
├─ Game list:       ✅ Returns stored games
│
└─ Result:         ✅ Everything available
```

---

## Code Flow - DB Check Pattern

```python
# All DB endpoints follow this pattern:

@router.get("/games")
async def list_games():
    
    if not DB_ENABLED:           # ← Check if DB configured
        return 503               # ← Return error gracefully
    
    # Otherwise proceed with DB operations
    games = await fetch_games()
    return games
```

This ensures:
- ✅ No crashes when DB is missing
- ✅ Clear error messages
- ✅ App stability

---

## When to Use Which Mode

```
NO DATABASE
│
├─ Learning chess programming
├─ Testing analysis algorithms
├─ Building analysis features
├─ Local development
├─ One-off position analysis
│
└─ Minimal setup, core features only


WITH DATABASE
│
├─ Production deployment
├─ Storing game libraries
├─ Building game archives
├─ Analysis session tracking
├─ Caching evaluations
│
└─ Full feature set, data persistence
```

---

## Migration Path

```
Start Here              Later (When Needed)
┌──────────────┐        ┌──────────────┐
│  No Database │   →    │  Add Database│
├──────────────┤        ├──────────────┤
│ • Analyze    │        │ • Store PGNs │
│ • Render     │        │ • Game lib   │
│ • Core features       │ • History    │
└──────────────┘        └──────────────┘
     ✅                       ✅
  Runs great!            Full features!

No code changes needed to add DB later! ✅
```

---

## Summary

The Chess Analyzer is designed to work **standalone without a database** while supporting **optional database features** when needed.

Think of it as:
- **Core:** Board + Analysis (always works)
- **Optional:** PGN Storage (add when needed)

🎯 **Start simple, add complexity only when you need it!**

