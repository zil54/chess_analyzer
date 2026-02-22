# Stockfish Integration with Database Caching

## Overview

The chess analyzer now implements a **cache-then-compute pattern** for Stockfish evaluations:

1. **Check Cache**: When analyzing a position (FEN), the system first checks if an evaluation already exists in the database
2. **Compute if Needed**: If the FEN isn't in the cache, Stockfish runs the analysis
3. **Store Result**: The evaluation is stored in the database for future use
4. **Return**: The evaluation is returned to the client

This architecture provides:
- **Performance**: Avoid re-analyzing identical positions
- **Scalability**: Build up a knowledge base over time
- **Consistency**: All evaluations are persistent and traceable
- **Flexibility**: Optional force-recompute to update evaluations

## Architecture

### Database Schema

The `evals` table (already in your schema) stores evaluations:

```sql
CREATE TABLE public.evals (
    fen TEXT PRIMARY KEY,
    best_move TEXT,              -- Best move in UCI format (e.g., "e2e4")
    score_cp INT,                -- Score in centipawns from White's perspective
    score_mate INT,              -- Mate score (positive = White mates, negative = Black mates)
    depth INT,                   -- Search depth achieved
    pv TEXT,                     -- Principal variation (best continuation as UCI moves)
    created_at TIMESTAMP         -- When the evaluation was created
);
```

**Key Design Choices**:
- **FEN as PRIMARY KEY**: Each position is unique, making FEN a natural primary key
- **Separate score_cp and score_mate**: Handles both endgame evaluations and mate scores
- **PV (Principal Variation)**: Stores the best continuation for deeper analysis
- **Depth field**: Allows tracking evaluations at different search depths

### File Structure

```
app/backend/
├── services/
│   └── analyzer_service.py       # Stockfish integration + caching logic
├── api/
│   └── routes.py                 # /analyze endpoint
└── db/
    └── db.py                     # Database functions (upsert_eval, get_eval)
```

## Implementation Details

### analyzer_service.py

```python
async def analyze_position(
    fen: str,
    depth: int = 20,
    time_limit: float = 0.5,
    force_recompute: bool = False
) -> Dict:
```

**Parameters**:
- `fen`: Chess position in FEN notation
- `depth`: Maximum search depth (default 20)
- `time_limit`: Time limit in seconds (default 0.5)
- `force_recompute`: Skip cache and always run Stockfish

**Returns**:
```json
{
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "best_move": "e2e4",
    "score_cp": 20,
    "score_mate": null,
    "depth": 20,
    "pv": "e2e4 e7e5 g1f3 nc6",
    "cached": false,
    "created_at": "2026-02-21T12:39:17.142582"  // only if cached
}
```

**Process**:
1. Validate FEN (returns error if invalid)
2. Check database cache (if DB enabled and not force_recompute)
3. If cache hit: return cached evaluation with `"cached": true`
4. If cache miss: run Stockfish with specified depth/time
5. Store result in database (if DB enabled)
6. Return evaluation with `"cached": false`

### routes.py - `/analyze` Endpoint

```
POST /analyze
Content-Type: application/json

Request:
{
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "depth": 20,
    "time_limit": 0.5,
    "force_recompute": false
}

Response: (same as analyze_position return value)
```

**Error Responses**:
- `400 Bad Request`: Missing FEN or invalid FEN format
- `500 Internal Server Error`: Stockfish execution failed
- `503 Service Unavailable`: Database not configured (for DB-only operations)

## Workflow Examples

### Example 1: Analyzing Starting Position (First Time)

```
Client Request:
POST /analyze
{ "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" }

Backend Process:
1. Check DB → Not found (cache miss)
2. Run Stockfish → Returns analysis
3. Store in evals table
4. Return analysis with cached=false

Response:
{
    "fen": "...",
    "best_move": "e2e4",
    "score_cp": 20,
    "depth": 20,
    "cached": false
}
```

### Example 2: Analyzing Same Position Again

```
Client Request:
POST /analyze
{ "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" }

Backend Process:
1. Check DB → Found! (cache hit)
2. Return cached result
3. No Stockfish execution needed

Response:
{
    "fen": "...",
    "best_move": "e2e4",
    "score_cp": 20,
    "depth": 20,
    "cached": true,
    "created_at": "2026-02-21T12:39:17.142582"
}

Performance: Instant response vs 0.5+ seconds without cache
```

### Example 3: Force Recompute

```
Client Request:
POST /analyze
{
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "force_recompute": true
}

Backend Process:
1. Skip DB check
2. Run Stockfish
3. Update evals table (ON CONFLICT DO UPDATE)
4. Return analysis with cached=false

Use Cases:
- Get deeper analysis (increase depth parameter)
- Update evaluation after engine improvements
- Refresh outdated evaluations
```

## Database Operations

### Cache Lookup

```python
async def get_eval(fen: str) -> Optional[Dict]:
    # Returns existing evaluation or None if not found
```

### Cache Store/Update

```python
async def upsert_eval(
    fen: str,
    best_move: str = None,
    score_cp: int = None,
    score_mate: int = None,
    depth: int = None,
    pv: str = None
) -> None:
    # Inserts new or updates existing evaluation
    # Uses PostgreSQL ON CONFLICT clause
```

## Performance Characteristics

| Scenario | Time | Notes |
|----------|------|-------|
| Cache hit | <10ms | Direct DB lookup + return |
| Cache miss (new) | 0.5-2s | Depends on time_limit and position complexity |
| Force recompute | 0.5-2s | Always runs Stockfish |
| After 100 games | 90%+ cache hits | Typical opening positions cached |

## Integration with PGN Upload

When a PGN is uploaded:

1. **Create Game**: Insert game metadata into `games` table
2. **Create Moves**: Insert all positions into `moves` table with FENs
3. **Optional**: Analyze all positions
   ```python
   # Future enhancement
   for move in game_moves:
       eval = await analyze_position(move.fen)
       # Evals now cached for rapid replay
   ```

## Error Handling

The service gracefully handles:

| Error | Response | Recovery |
|-------|----------|----------|
| Invalid FEN | 400 Bad Request | Client should validate FEN |
| Stockfish not found | 500 Internal Error | Deploy sf.exe in engine/ folder |
| DB connection error | Logs warning, continues | Service degrades to no-cache mode |
| Analysis timeout | Returns partial result | Increases time_limit for deeper analysis |

## Configuration

In `.env` file:

```env
# Database connection (required for caching)
DATABASE_URL=postgresql://postgres:YUG0slavia@localhost:5432/chess_analyzer

# OR use individual components
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chess_analyzer
DB_USER=postgres
DB_PASSWORD=YUG0slavia
```

If `DATABASE_URL` is not set:
- Caching is disabled
- Stockfish still works (no persistence)
- All endpoints function normally (slower for repeated positions)

## Testing

Run the test suite:

```bash
# All tests
pytest testing/test_analyze_endpoint.py -v

# Specific test
pytest testing/test_analyze_endpoint.py::test_analyze_cache_hit -v

# With output
pytest testing/test_analyze_endpoint.py -v -s
```

**Test Coverage**:
- ✓ Valid FEN analysis
- ✓ Cache hits on repeated positions
- ✓ Force recompute bypass
- ✓ Invalid FEN error handling
- ✓ Missing FEN error handling
- ✓ Response structure validation

## Future Enhancements

1. **Batch Analysis**: Analyze all FENs from uploaded PGN in background
2. **Deeper Analysis**: Queue long-running analysis for strong positions
3. **Opening Book**: Serve known opening evaluations without Stockfish
4. **Time Management**: Adjust time_limit based on position complexity
5. **Transposition Tables**: Share evaluation across different move orders
6. **Web Sockets**: Real-time depth progression like Lichess

## Troubleshooting

### No evaluations cached in database

```bash
# Check if DB is enabled
curl http://localhost:8000/health/db

# Check evals table
psql -U postgres -d chess_analyzer -c "SELECT COUNT(*) FROM evals;"

# Verify .env has DATABASE_URL
cat .env | grep DATABASE_URL
```

### Stockfish not found error

```bash
# Verify sf.exe location
ls app/engine/sf.exe

# Ensure it's executable
chmod +x app/engine/sf.exe  # Linux/Mac
```

### Analysis takes too long

```python
# Reduce time_limit or depth
POST /analyze
{
    "fen": "...",
    "depth": 10,           # Reduced from 20
    "time_limit": 0.2      # Reduced from 0.5
}
```

## API Documentation

See `routes.py` `/analyze` endpoint for full documentation with examples.

Call with:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "depth": 20,
    "time_limit": 1.0
  }'
```

