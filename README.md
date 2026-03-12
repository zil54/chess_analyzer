# Chess Analyzer

A full-stack chess analysis application that combines Stockfish engine integration with a modern web interface for analyzing chess games in real-time.

<img width="774" height="748" alt="Chess Analyzer Interface" src="https://github.com/user-attachments/assets/a3f7700b-491c-4ecb-a465-83e5411829cf" />

## Features

- **Real-time Chess Analysis**: Stream Stockfish evaluations directly to the UI as analysis progresses
- **PGN Upload & Analysis**: Upload PGN files and automatically analyze all positions
- **Line 1, 2, 3 Display**: View the top 3 principal variations at each depth level
- **Interactive Chess Board**: Click squares to set positions or navigate through games
- **Depth Control**: Set custom evaluation depths for analysis
- **Database Integration**: Store analyzed positions, games, and evaluation lines in PostgreSQL
- **No-Database Mode**: Fully functional without database for quick analysis
- **WebSocket Streaming**: Real-time updates to the frontend during analysis
- **Flip Board**: Quick board orientation toggle
- **Game Navigation**: Navigate through uploaded PGN games with move-by-move analysis

## Architecture

```
chess_analyzer/
├── app/
│   ├── backend/          # FastAPI backend server
│   │   ├── api/         # REST API endpoints
│   │   ├── db/          # Database connectivity (psycopg)
│   │   ├── logs/        # Logging configuration
│   │   ├── services/    # Business logic
│   │   ├── svg/         # Chess board SVG generation
│   │   ├── main.py      # FastAPI application entry
│   │   └── requirements.txt
│   ├── engine/          # Stockfish integration
│   │   ├── engine.py    # Engine wrapper
│   │   ├── stockfish_session.py  # Session management
│   │   └── sf.exe       # Stockfish executable
│   └── frontend/        # Vite + Vue.js frontend
│       ├── src/
│       ├── index.html
│       └── package.json
├── testing/             # Consolidated test suite
│   ├── conftest.py
│   ├── test_*.py
│   └── ...
├── documentation/       # Additional guides
└── README.md
```

## Prerequisites

- **Python 3.10+** (with venv)
- **Node.js 18+** (for frontend)
- **PostgreSQL 12+** (optional, for database features)
- **Stockfish** (included as `app/engine/sf.exe`)

## Quick Start

### 1. Setup Backend

```bash
cd <project-root>

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r app/backend/requirements.txt

# Optional: Configure database in .env
# DATABASE_URL=postgresql://postgres:<your password>@localhost:5432/chess_analyzer
```

### 2. Setup Frontend

```bash
cd app/frontend

# Install dependencies
npm install

# Development server with hot reload
npm run dev

# Or build for production
npm run build
```

### 3. Run the Application

```bash
# Start backend server
python -m app.backend.main
# Server runs on http://localhost:8000

# In another terminal, frontend dev server
cd app/frontend
npm run dev
# Frontend available at http://localhost:5173
```

## Usage

### Analyzing Starting Position
1. Open the application in your browser
2. Click "Analyze (Live)"
3. The UI starts showing analysis as soon as data is available
4. With the current defaults, the UI requests display depth `10` while the worker continues to depth `70`
5. If database cache exists, the UI can show a cached snapshot first and then continue deepening live

### Live Analysis Behavior

The live-analysis flow uses three separate concepts:

- **Display target depth** - when the UI has reached a useful minimum depth
- **Worker target depth** - when the background analysis job is allowed to stop
- **Display lag depth** - how far behind the worker the displayed snapshot is allowed to be

Current default values:

- **Display target**: `10`
- **Worker target**: `70`
- **Display lag**: `2`

#### Without Database

When the database is disabled or not configured:

- the app streams directly from Stockfish over WebSocket
- there is no cache lookup
- the first visible depth can be very low (including depth 1)
- the UI trails the worker by about `display_lag_depth`
- no analysis is persisted

#### With Database

When the database is enabled:

- the app first looks for a stored analysis snapshot for the FEN
- if found, it sends a cached snapshot immediately
- then it starts or reuses a worker to deepen further
- the worker can continue beyond the requested display target so the cache improves over time
- snapshots are persisted while analysis is running

#### Cached Snapshot Selection

When multiple cached depths exist:

- the backend tracks the deepest stored depth for worker progress
- for display, it prefers a **richer multi-line snapshot** over a slightly deeper snapshot that only has line 1
- this keeps the UI from regressing from 3 lines to 1 line just because a deeper partial depth was stored first

#### Cached Positions Can Deepen Further

If a cached position already exceeds the requested worker target, the coordinator may still deepen further instead of stopping immediately.

Example:

- requested worker target: `70`
- cached depth: `72` is impossible because max is `70`
- requested worker target: `26`
- cached depth: `41`
- effective worker target becomes `47`

The only time cached analysis ends immediately is when the cached position is already at the configured maximum depth.

#### Status Text in the UI

Representative status text now looks like:

- `Live analysis · showing depth 8/10 · worker 10/70`
- `Serving cached depth 40 while worker deepens to 46 · showing depth 40 (requested 10) · worker 40/46`
- `Analysis complete · showing depth 26 (requested 10) · worker 26/26`

### Uploading PGN Files
1. Click "Upload PGN" button
2. Select a PGN file from your computer
3. The file is parsed and loaded into the UI
4. If the database is enabled, the game and analysis can be persisted
5. If the database is disabled, navigation still works but persistence does not

### Setting Custom Position
1. Use the chess board interface to set up pieces
2. Or paste FEN notation (when FEN feature is enabled)
3. Click "Analyze (Live)" to evaluate

### Navigation
- **Move through game**: Use arrow keys or click moves
- **Flip board**: Click "Flip" button
- **Live analysis defaults**: UI target depth `10`, worker target depth `70`, display lag `2`
- **View variations**: Check Line 1, 2, 3 for top moves

## Database Setup (Optional)

If you want to persist analyzed positions and games:

```bash
# Create PostgreSQL database
createdb chess_analyzer

# Create tables (schema will auto-initialize on first run)
```

The following tables are automatically created:
- **games**: Stores uploaded PGN games
- **moves**: Stores individual moves with FEN positions
- **evals**: Stores Stockfish evaluations at specific depths
- **analysis_lines**: Stores principal variation lines

### Environment Configuration

Create a `.env` file in the project root:

```env
# Database configuration (optional)
DATABASE_URL=postgresql://postgres:<your password>@localhost:5432/chess_analyzer

# Backend live-analysis defaults
LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH=10
LIVE_ANALYSIS_WORKER_TARGET_DEPTH=70
LIVE_ANALYSIS_DISPLAY_LAG_DEPTH=2
```

If you run the Vite dev server from `app/frontend`, you can also create `app/frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH=10
VITE_LIVE_ANALYSIS_WORKER_TARGET_DEPTH=70
VITE_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH=2
```

Use `.env.example` in the repo root and `app/frontend/.env.example` as templates.

## Testing

All tests are consolidated in the `testing/` folder:

```bash
# Run all tests
pytest testing/

# Run specific test file
pytest testing/test_analyze_endpoint.py

# Run with verbose output
pytest testing/ -v

# Run tests matching pattern
pytest testing/ -k "pgn"
```

### Key Test Files
- `test_connectivity.py` - Database connection tests
- `test_upload_pgn_db.py` - PGN upload and storage
- `test_analyze_endpoint.py` - WebSocket analysis endpoint
- `test_stockfish_direct.py` - Direct Stockfish integration
- `test_pgn_auto_analysis.py` - Automatic analysis on upload

## API Endpoints

### REST API
- `GET /` - Serve frontend
- `POST /svg` - Get board SVG for a position
- `POST /games` - Upload PGN file
- `GET /games` - List uploaded games

### WebSocket
- `WS /ws/analyze` - real-time live analysis stream
  - Send example:
    ```json
    {
      "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "display_target_depth": 10,
      "worker_target_depth": 70,
      "display_lag_depth": 2
    }
    ```
  - Legacy `depth` is still accepted and maps to `display_target_depth`
  - Receive snapshot/status payloads that include fields such as:
    - `depth`
    - `display_target_depth`
    - `worker_target_depth`
    - `worker_depth`
    - `worker_running`
    - `lines`

## Configuration

### Live Analysis Defaults
- **Backend env**: `LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH`, `LIVE_ANALYSIS_WORKER_TARGET_DEPTH`, `LIVE_ANALYSIS_DISPLAY_LAG_DEPTH`
- **Frontend env**: `VITE_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH`, `VITE_LIVE_ANALYSIS_WORKER_TARGET_DEPTH`, `VITE_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH`
- **Fallback defaults**: display target `10`, worker target `70`, UI lag `2`
- **Maximum depth clamp**: `70`

### Depth Settings
- **Display target depth**: default `10`
- **Worker target depth**: default `70`
- **Display lag depth**: default `2`
- **Top lines shown**: up to 3 principal variations

### Persistence Notes
- In DB-backed live analysis, cached snapshots can be shown immediately and then deepened further
- The `evals` table stores the latest best line for a FEN
- The `analysis_lines` table stores per-depth principal-variation snapshots used by the live-analysis panel
- No-DB mode performs live analysis only; it does not persist cached snapshots

### Evaluation Update Strategy
- **No DB**: direct live engine stream only
- **With DB**: cached snapshot first when available, then deeper background analysis with DB updates
