# Can the App Run Without a Database?

## Short Answer
**Yes.** The app can run without PostgreSQL for live analysis, board rendering, and PGN exploration. What you lose is persistence and DB-backed cached analysis.

---

## What Works WITHOUT a Database

### ✅ Core Features
1. **Board SVG Rendering** (`POST /svg`)
   - Send a FEN string → get an SVG board
   - No database required

2. **Live Stockfish Analysis** (`WebSocket /ws/analyze`)
   - Streams analysis directly from Stockfish
   - No DB lookup is performed
   - First visible depth can be very low (including depth 1)
   - The UI trails the worker by the configured display lag

3. **Analysis Display**
   - Shows depth, evaluation, and up to 3 PV lines
   - Uses the current frontend defaults:
     - display target depth `10`
     - worker target depth `70`
     - display lag depth `2`
   - No persistence required

4. **PGN Upload and Move Navigation**
   - PGN files can still be parsed and loaded into the UI
   - Move-by-move board navigation still works
   - Without DB, uploaded games are not persisted

5. **Frontend UI**
   - Full Vue.js interface loads and functions without DB

---

## What Changes Without a Database

### No Cache Layer
Without DB:

- there is no stored evaluation lookup
- there is no cached snapshot to show first
- every live-analysis request starts from direct engine output
- results are not reused between sessions

### No Persistence
Without DB:

- games are not stored permanently
- engine analysis is not written to `evals`
- principal-variation snapshots are not written to `analysis_lines`
- refreshing or restarting loses uploaded PGNs and live-analysis cache

---

## Current Live Analysis Behavior Without DB

When `DB_ENABLED = False`, the backend uses the direct-engine WebSocket path.

### Request Model
The frontend sends a request like:

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "display_target_depth": 10,
  "worker_target_depth": 70,
  "display_lag_depth": 2
}
```

### Runtime Behavior
- Stockfish starts immediately
- the UI can begin showing shallow depths right away
- the displayed depth trails the worker by about 2 plies
- analysis stops when the worker reaches depth 70 (unless you override the defaults)

### Representative UI Text
You may see status text like:

- `Live analysis · showing depth 6/10 · worker 8/70`
- `Analysis complete · showing depth 70 (requested 10) · worker 70/70`

---

## What DOES NOT Work Without a Database

### ❌ DB-Backed Features
These features require PostgreSQL:

- persistent game library/history
- reloading previously uploaded games from storage
- cached live-analysis snapshots from `evals` / `analysis_lines`
- DB health checks that report a live PostgreSQL connection

### Endpoints That Depend on Stored DB Data
These routes are only useful with a configured database:

| Endpoint | Why it depends on DB |
|----------|----------------------|
| `GET /games` | Reads persisted games |
| `GET /games/{id}/moves` | Reads persisted move history |
| `GET /evals` | Reads persisted cached evaluations |
| `GET /health/db` | Reports database connectivity |

---

## How to Run Without Database

### 1. Leave DB settings unset

```env
# DATABASE_URL=postgresql://user:pass@localhost:5432/chess_analyzer
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

### 2. Start the backend

```bash
cd app/backend
python main.py
```

### 3. Optional: run the frontend dev server

```bash
cd app/frontend
npm run dev
```

### 4. You can now
- ✅ Open the frontend UI
- ✅ Render boards from FEN strings
- ✅ Upload a PGN for local exploration
- ✅ Run live Stockfish analysis
- ✅ Navigate through moves in the UI

### 5. You cannot persist
- ❌ uploaded games
- ❌ cached evaluations
- ❌ analysis lines
- ❌ game history across restarts

---

## How This Differs From DB Mode

### Without DB
- always starts from direct engine output
- no cached snapshot is shown first
- no saved analysis is reused
- no results are persisted

### With DB
- can show a cached snapshot immediately
- can prefer richer multi-line cached snapshots over deeper one-line snapshots
- can deepen cached positions further in the background
- persists analysis data for later reuse

---

## Summary Table

| Feature | Without DB | With DB |
|---------|-----------|---------|
| Frontend UI | ✅ Works | ✅ Works |
| Board Rendering | ✅ Works | ✅ Works |
| Live Analysis | ✅ Works | ✅ Works |
| PGN Parsing | ✅ Works | ✅ Works |
| PGN Move Navigation | ✅ Works | ✅ Works |
| Cached Snapshots | ❌ No | ✅ Yes |
| PGN Persistence | ❌ No | ✅ Yes |
| Game Library | ❌ No | ✅ Yes |
| Evaluation Cache | ❌ No | ✅ Yes |

---

## Recommended Configuration

### Minimal Setup (No DB)
```bash
# Stockfish only
python main.py
```

### Full Setup (With DB)
```bash
# Stockfish + PostgreSQL
# Set DATABASE_URL or DB_* settings in .env
python main.py
```

Both configurations start successfully. The difference is whether analysis state is persisted and reused.
