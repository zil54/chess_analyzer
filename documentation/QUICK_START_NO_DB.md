# Quick Reference: Database vs No-Database Mode

## TL;DR

**Yes, the app works without a database.** You can analyze chess positions, render boards, and stream live engine evaluations. You just can't persist PGN files to a database.

---

## Feature Availability

### Works Without Database ✅
```
✅ Frontend UI
✅ Chess board SVG rendering from FEN
✅ Real-time Stockfish analysis via WebSocket
✅ Evaluation lines (principal variations)
✅ Depth display
✅ Board flip
✅ FEN input/manipulation
```

### Requires Database ❌
```
❌ PGN file upload (no persistence)
❌ Game library/history
❌ Session tracking
❌ Cached evaluations
```

---

## Setup Comparison

### Minimal Setup (Database NOT Required)
```env
# .env file - empty or no DATABASE_URL
```

**Result:** 
- App starts ✅
- Core analysis works ✅  
- PGN upload doesn't persist ❌

### Full Setup (Database Required for All Features)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/chess_analyzer
```

**Result:**
- App starts ✅
- Core analysis works ✅
- PGN upload persists ✅
- Game library works ✅

---

## What Actually Happens

### Without DATABASE_URL Set

**On Startup:**
```
[WARNING] Database is NOT configured. Session/PGN features will be unavailable.
```

**When User Uploads PGN:**
- PGN is parsed ✅
- Moves are calculated ✅
- Game is NOT saved to database ❌
- User sees: Can't retrieve uploaded games

**When User Tries to Load Games:**
```
503 Service Unavailable
Database not configured. Set DATABASE_URL in .env to enable.
```

---

## Affected Endpoints

| Endpoint | Status Without DB |
|----------|------------------|
| `GET /` | ✅ Works |
| `POST /svg` | ✅ Works |
| `WebSocket /ws/analyze` | ✅ Works |
| `POST /analyze_pgn` | ⚠️ Parses but won't persist |
| `POST /games` | ❌ 503 Error |
| `GET /games` | ❌ 503 Error |
| `GET /games/{id}/moves` | ❌ 503 Error |
| `GET /evals` | ❌ 503 Error |

---

## Decision Tree

```
Want to use the app?
├─ YES, just analyze positions
│  └─ Don't set DATABASE_URL ✅
│     Works: FEN input + Stockfish + Live analysis
│
└─ YES, also save game libraries
   └─ Set DATABASE_URL ✅
      Works: Everything including PGN persistence
```

---

## Recommendation

**Start without database if:**
- You're testing/developing the analysis features
- You don't need to save games
- You want minimal setup

**Add database when:**
- You want to keep a game library
- You need to persist analysis sessions
- You want evaluation caching

The architecture supports both modes seamlessly! 🎯

