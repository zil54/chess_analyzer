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
2. Click "Analyze (Live)" button
3. Watch real-time evaluation updates in Line 1, 2, 3
4. Evaluations display as depth increases

### Uploading PGN Files
1. Click "Upload PGN" button
2. Select a PGN file from your computer
3. Games are parsed and stored in the database
4. Click any game to analyze it

### Setting Custom Position
1. Use the chess board interface to set up pieces
2. Or paste FEN notation (when FEN feature is enabled)
3. Click "Analyze (Live)" to evaluate

### Navigation
- **Move through game**: Use arrow keys or click moves
- **Flip board**: Click "Flip" button
- **Change depth**: Adjust depth slider (max typically 46)
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

# Log level
LOG_LEVEL=INFO
```

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
- `GET /board?fen=...` - Get board SVG for position
- `POST /games` - Upload PGN file
- `GET /games` - List uploaded games

### WebSocket
- `WS /analyze` - Real-time analysis stream
  - Send: `{"fen": "...", "depth": 30}`
  - Receive: `{"depth": 20, "line1": "e2e4 e7e5...", "score": 25, ...}`

## Configuration

### Depth Settings
- **Minimum storage depth**: 15
- **Max depth**: 46 (configurable)
- **Line storage**: Top 3 variations per depth

### Evaluation Update Strategy
- Depths 1-14: Streamed to UI only (not stored)
- Depths 15+: Stored in database + streamed to UI

## Troubleshooting

### "Database is NOT configured" Warning
This is normal if you don't have PostgreSQL set up. The app works fine without it.

### WebSocket Connection Issues
- Ensure backend is running on `http://localhost:8000`
- Check browser console for specific errors
- Verify CORS settings if frontend is on different port

### Stockfish Not Found
- Verify `app/engine/sf.exe` exists
- On Linux/Mac: Ensure Stockfish is installed and in PATH

### PGN Upload Not Working
- Verify DATABASE_URL is set in `.env`
- Check PostgreSQL is running
- Review backend logs for SQL errors

## Project Structure Details

### Backend
- **main.py**: FastAPI app setup, WebSocket handlers
- **api/routes.py**: REST endpoints
- **db/db.py**: Database operations (psycopg)
- **services/**: Business logic (PGN parsing, etc.)
- **svg/svg.py**: Chess board SVG generation

### Frontend
- **index.html**: Entry point
- **src/App.vue**: Main application component
- **src/components/**: Board, evaluation display, controls

### Engine
- **engine.py**: Stockfish process management
- **stockfish_session.py**: UCI protocol implementation

## Performance Notes

- Analysis updates stream in real-time via WebSocket
- Database storage happens asynchronously
- UI remains responsive during deep analysis
- Evaluation lines persist across sessions if DB enabled

## Contributing

When adding features:
1. Add tests to `testing/` folder
2. Update this README with new endpoints/features
3. Follow existing code style and patterns
4. Test both with and without database


## Support

For issues or questions:
1. Check the `documentation/` folder for detailed guides
2. Review test files for usage examples
3. Check logs in `app/backend/logs/`

## Documentation

Additional detailed documentation is available in `documentation/`:
- `STOCKFISH_INTEGRATION.md` - Engine integration details
- `PGN_UPLOAD_AUTO_ANALYSIS.md` - PGN handling guide
- `RUN_WITHOUT_DATABASE.md` - No-database setup guide
- `QUICK_START_NO_DB.md` - Quick setup without database

---

**Current Status**: Fully functional with real-time analysis, PGN support, and optional PostgreSQL integration.


