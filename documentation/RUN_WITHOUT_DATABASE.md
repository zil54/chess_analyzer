# Can the App Run Without a Database?

## Short Answer
**Yes, partially.** The core chess analysis features work without a database, but PGN upload persistence won't work.

---

## What Works WITHOUT a Database

### ✅ Core Features
1. **Board SVG Rendering** (`POST /svg`)
   - Send a FEN string → get SVG board visualization
   - No database required

2. **Live Stockfish Analysis** (`WebSocket /ws/analyze`)
   - Real-time engine analysis via WebSocket
   - Streams multi-PV evaluation lines
   - No database required

3. **Analysis Display**
   - Shows depth, evaluation, and principal variation lines
   - All computation done by Stockfish
   - No database required

4. **Board Navigation**
   - Flip board orientation
   - View different positions (if manually entered)
   - No database required

5. **Frontend UI**
   - Full Vue.js interface loads and functions
   - All visualization components work
   - No database required

---

## What DOES NOT Work Without a Database

### ❌ Database-Dependent Features
These endpoints return `503 Service Unavailable` when `DB_ENABLED = False`:

| Endpoint | Feature | Why Fails |
|----------|---------|-----------|
| `POST /analyze_pgn` | PGN File Upload | Can parse PGN but won't persist |
| `POST /games` | Store PGN to DB | Explicitly requires DB |
| `GET /games` | List all games | Needs to query database |
| `GET /games/{id}/moves` | Retrieve moves for a game | Needs database query |
| `GET /evals` | Fetch cached evaluations | Requires database |
| `GET /health/db` | DB health check | Returns DB disabled status |

---

## What Happens Without DATABASE_URL

When `DATABASE_URL` is not set in `.env`:

### Application Startup
```
[WARNING] Database is NOT configured. 
Session/PGN features will be unavailable. 
Set DATABASE_URL in .env to enable.
```

### User Attempts to Upload PGN
- User clicks "Upload PGN" button
- File is sent to `/analyze_pgn`
- Endpoint parses the PGN ✅
- **Then tries to save to DB ❌**
- User sees error: PGN is analyzed but not saved
- Database is skipped but upload incomplete

---

## Endpoints That DON'T Require Database

### 1. GET / (Frontend)
- Serves the Vue.js application
- Works perfectly without DB

### 2. POST /svg
```json
Request:  { "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" }
Response: <svg>...</svg>
```
Works without DB ✅

### 3. WebSocket /ws/analyze
```
Client: sends FEN string
Server: streams Stockfish analysis lines
```
Works without DB ✅

### 4. POST /analyze (if it exists)
One-shot analysis endpoint
Works without DB ✅

---

## How to Run Without Database

### 1. Don't set `DATABASE_URL` in `.env`
```env
# Leave this commented or unset:
# DATABASE_URL=postgresql://user:pass@localhost/chess_analyzer

# Or use separate vars without complete credentials:
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

### 2. Start the app normally
```bash
cd app/backend
python main.py
```

### 3. You can now:
- ✅ Open the frontend UI
- ✅ Render chess boards from FEN strings
- ✅ Analyze positions with Stockfish in real-time
- ✅ View evaluation lines and depth

### 4. You CANNOT:
- ❌ Upload PGN files (they won't persist)
- ❌ Retrieve previously uploaded games
- ❌ Store game analysis sessions
- ❌ Access cached evaluations

---

## Current Implementation Details

### DB_ENABLED Flag
In `app/backend/db/db.py`:
```python
DATABASE_URL = os.getenv("DATABASE_URL") or _build_database_url_from_parts()
DB_ENABLED = bool(DATABASE_URL)
```

### Graceful Degradation
The app checks `DB_ENABLED` before each database operation:
- If `False` → returns 503 "Database not configured"
- If `True` → attempts database operations

### No Hard Dependency
The application:
- Does NOT crash if DATABASE_URL is missing
- Does NOT require database to start up
- Logs warnings but continues running
- Gracefully handles DB absence per endpoint

---

## Ideal Use Cases

### Without Database ✅
- **Local analysis tool**: Analyze positions from FEN or textbox input
- **Engine testing**: Test Stockfish against different positions
- **Board visualization**: Convert PEN to SVG for web display
- **Real-time analysis**: Stream live engine evaluations

### With Database ✅
- **Game library**: Store and retrieve uploaded PGN files
- **Analysis sessions**: Track multiple game analyses
- **Evaluation caching**: Store engine evaluations for quick lookup
- **Game history**: Maintain game library over time

---

## Summary Table

| Feature | Without DB | With DB |
|---------|-----------|---------|
| Frontend UI | ✅ Works | ✅ Works |
| Board Rendering | ✅ Works | ✅ Works |
| Live Analysis | ✅ Works | ✅ Works |
| FEN Input | ✅ Works | ✅ Works |
| PGN Parsing | ✅ Works | ✅ Works |
| PGN Persistence | ❌ No | ✅ Yes |
| Game Library | ❌ No | ✅ Yes |
| Session Tracking | ❌ No | ✅ Yes |
| Eval Caching | ❌ No | ✅ Yes |

---

## Recommended Configuration

### Minimal Setup (No DB)
```bash
# Just need Stockfish
# No DATABASE_URL required
python main.py
```

### Full Setup (With DB)
```bash
# Set DATABASE_URL in .env
# Stockfish + PostgreSQL required
python main.py
```

Both configurations work and fail gracefully on unavailable resources.

