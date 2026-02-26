from fastapi import APIRouter, HTTPException, Request, Response
import chess
import chess.pgn
import chess.svg
import io

try:
    from app.backend.db.db import (
        create_game,
        insert_moves,
        get_moves,
        get_eval,
        DB_ENABLED,
    )
except Exception:
    DB_ENABLED = False

# Logger (fallback to stdlib if app logger isn't available)
try:
    from app.backend.logs.logger import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("chess-analyzer")

router = APIRouter()

@router.post("/analyze_pgn")
async def analyze_pgn(request: Request):
    """
    Parse a PGN and return all positions.
    If DB_ENABLED, also persist the game and moves to the database.
    Accepts either JSON with {"pgn": "..."} or multipart file upload
    """
    try:
        # Try JSON first
        data = await request.json()
        pgn_str = data.get("pgn", "")
    except Exception:
        # Try form data with file upload
        try:
            form = await request.form()
            if "file" in form:
                file = form["file"]
                pgn_text = await file.read()
                pgn_str = pgn_text.decode('utf-8')
            elif "pgn" in form:
                pgn_str = form["pgn"]
            else:
                raise HTTPException(status_code=400, detail="No PGN data provided")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PGN: {str(e)}")

    if not pgn_str:
        raise HTTPException(status_code=400, detail="PGN data is required")

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if not game:
            raise ValueError("No valid game found in PGN")

        # Extract game metadata
        headers = {
            "event": game.headers.get("Event", "Unknown"),
            "white": game.headers.get("White", "Unknown"),
            "black": game.headers.get("Black", "Unknown"),
            "date": game.headers.get("Date", "Unknown"),
            "result": game.headers.get("Result", "*"),
            "site": game.headers.get("Site", "Unknown"),
        }

        board = game.board()
        positions = []
        move_rows = []

        # Add starting position
        positions.append({
            "move_number": 0,
            "fen": board.fen(),
            "move": None,
            "san": None
        })

        # Store starting position as ply 0
        move_rows.append({
            "ply": 0,
            "san": "START",
            "fen": board.fen(),
            "comment": None,
            "cp_tag": False,
        })

        # Process all moves
        ply = 0
        node = game
        for move in game.mainline_moves():
            ply += 1
            san = board.san(move)
            board.push(move)

            # Try to capture comments
            try:
                node = node.variation(move)
                comment = (node.comment or None) if node else None
            except Exception:
                comment = None

            positions.append({
                "move_number": board.fullmove_number,
                "fen": board.fen(),
                "move": move.uci(),
                "san": san
            })

            move_rows.append({
                "ply": ply,
                "san": san,
                "fen": board.fen(),
                "comment": comment,
                "cp_tag": False,
            })

        # Persist to DB if enabled
        game_id = None
        if DB_ENABLED:
            try:
                logger.info(f"Persisting PGN to database (analyze_pgn endpoint)...")
                game_id = await create_game(pgn_str, headers)
                logger.info(f"Game created with ID: {game_id}")

                await insert_moves(game_id, move_rows)
                logger.info(f"Moves inserted successfully ({len(move_rows)} rows)")
            except Exception as e:
                logger.error(f"DB error during insert in analyze_pgn: {e}", exc_info=True)
                # Don't fail the entire request; still return positions from parsing

        return {
            "success": True,
            "game_id": game_id,
            "headers": headers,
            "total_moves": len(positions) - 1,
            "positions": positions
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid PGN format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PGN: {str(e)}")

@router.post("/svg")
async def render_svg(request: Request):
    data = await request.json()
    fen = data.get("fen")
    flip = data.get("flip", False)
    if not fen:
        raise HTTPException(status_code=400, detail="Missing FEN")

    try:
        board = chess.Board(fen)
        # Render with orientation based on flip flag
        svg = chess.svg.board(board, orientation=chess.BLACK if flip else chess.WHITE)
        return Response(content=svg, media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {str(e)}")

@router.post("/games")
async def create_game_from_pgn(request: Request):
    """Create a game from uploaded PGN, persist all positions (FENs) into DB.

    Accepts multipart/form-data with a `file` field (PGN), or JSON {"pgn": "..."}.
    Returns: { id, headers, total_moves }
    """
    logger.info("=== POST /games called ===")
    logger.info(f"DB_ENABLED: {DB_ENABLED}")

    if not DB_ENABLED:
        logger.error("DB not enabled, returning 503")
        raise HTTPException(status_code=503, detail="Database not configured. Set DATABASE_URL in .env file.")

    # Read PGN (file or json)
    pgn_str = ""
    try:
        data = await request.json()
        pgn_str = (data.get("pgn") or "").strip()
    except Exception:
        # Multipart/form-data: Starlette returns an UploadFile instance
        try:
            form = await request.form()
            file = form.get("file")
            if file is None:
                pgn_str = (form.get("pgn") or "").strip()
            else:
                # Starlette UploadFile has async read(); other objects might expose .file
                try:
                    pgn_bytes = await file.read()
                except Exception:
                    pgn_bytes = file.file.read() if getattr(file, "file", None) else b""

                if not pgn_bytes:
                    raise HTTPException(status_code=400, detail="Uploaded PGN file is empty")

                try:
                    pgn_str = pgn_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    # Some PGNs can be latin-1; keep it permissive.
                    pgn_str = pgn_bytes.decode("latin-1")

                pgn_str = pgn_str.strip()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PGN: {str(e)}")

    if not pgn_str:
        raise HTTPException(status_code=400, detail="PGN data is required")

    logger.info(f"Read PGN: {len(pgn_str)} bytes")

    # Parse + convert to move list
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if not game:
            raise ValueError("No valid game found in PGN")

        headers = {
            "event": game.headers.get("Event", "Unknown"),
            "site": game.headers.get("Site", "Unknown"),
            "white": game.headers.get("White", "Unknown"),
            "black": game.headers.get("Black", "Unknown"),
            "date": game.headers.get("Date", "Unknown"),
            "result": game.headers.get("Result", "*")
        }

        board = game.board()
        move_rows = []

        # Store starting position as ply 0 (san required by schema; use a stable placeholder)
        move_rows.append({
            "ply": 0,
            "san": "START",
            "fen": board.fen(),
            "comment": None,
            "cp_tag": False,
        })

        ply = 0
        node = game
        for mv in game.mainline_moves():
            ply += 1
            san = board.san(mv)
            board.push(mv)

            # Try to capture comments if present (PGN node comments attach to the node *after* the move)
            try:
                node = node.variation(mv)
                comment = (node.comment or None) if node else None
            except Exception:
                comment = None

            move_rows.append({
                "ply": ply,
                "san": san,
                "fen": board.fen(),
                "comment": comment,
                "cp_tag": False,
            })

        logger.info(f"Parsed {ply} plies from PGN")

    except ValueError as e:
        logger.error(f"Invalid PGN format: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid PGN format: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing PGN: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PGN: {str(e)}")

    try:
        logger.info(f"Calling create_game...")
        game_id = await create_game(pgn_str, headers)
        logger.info(f"Game created with ID: {game_id}")

        logger.info(f"Calling insert_moves with {len(move_rows)} rows...")
        await insert_moves(game_id, move_rows)
        logger.info(f"Moves inserted successfully")

    except Exception as e:
        logger.error(f"DB error during insert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

    logger.info(
        "Stored game_id=%s to DB (white=%s black=%s result=%s) with %s plies",
        game_id,
        headers.get("white"),
        headers.get("black"),
        headers.get("result"),
        ply,
    )

    return {
        "success": True,
        "id": game_id,
        "headers": headers,
        "total_moves": ply,
    }


@router.get("/games")
async def list_games():
    """Return all games from the database."""
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not configured. Set DATABASE_URL in .env file.")

    try:
        from app.backend.db.db import get_connection
        conn = await get_connection()
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT id, white, black, result, event, site, date, raw_pgn
                FROM public.games
                ORDER BY id DESC
            """)
            rows = await cur.fetchall()
        await conn.close()

        games = [
            {
                "id": r["id"],
                "white": r["white"],
                "black": r["black"],
                "result": r["result"],
                "event": r["event"],
                "site": r["site"],
                "date": r["date"]
            }
            for r in rows
        ]

        return {
            "success": True,
            "total_games": len(games),
            "games": games
        }
    except Exception as e:
        logger.error(f"Error fetching games: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching games: {str(e)}")


@router.get("/games/{game_id}/moves")
async def fetch_game_moves(game_id: int):
    """Return all stored moves/positions for a game."""
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not configured. Set DATABASE_URL in .env file.")
    rows = await get_moves(game_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Game not found or has no moves")

    # Frontend expects move_number/positions-like shape; translate ply -> move_number
    # but keep ply for precise indexing.
    positions = [
        {
            "ply": r["ply"],
            "move_number": r["ply"],
            "fen": r["fen"],
            "move": None,
            "san": None if r["san"] == "START" else r["san"],
            "comment": r.get("comment"),
            "cp_tag": r.get("cp_tag"),
            "color": r.get("color"),
        }
        for r in rows
    ]

    return {
        "success": True,
        "game_id": game_id,
        "total_moves": max(0, len(positions) - 1),
        "positions": positions,
    }


@router.get("/evals")
async def fetch_eval(fen: str):
    """Fetch a cached evaluation for a given FEN from Postgres."""
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not configured. Set DATABASE_URL in .env file.")
    row = await get_eval(fen)
    if not row:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return row

@router.get("/health/db")
async def health_db():
    """Health check to confirm this running backend process can reach Postgres."""
    if not DB_ENABLED:
        return {"ok": False, "db_enabled": False, "detail": "DATABASE_URL not configured"}

    try:
        from app.backend.db.db import check_connection
        ok = await check_connection()
        return {"ok": bool(ok), "db_enabled": True}
    except Exception as e:
        return {"ok": False, "db_enabled": True, "detail": str(e)}

@router.post("/analyze")
async def analyze_position(request: Request):
    """
    Analyze a chess position using Stockfish with caching.

    Cache-then-compute pattern:
    1. Check if evaluation exists in DB (cache hit)
    2. If not found, run Stockfish (cache miss)
    3. Store result in DB
    4. Return evaluation

    Request body (JSON):
    {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "depth": 20,              // optional, default 20
        "time_limit": 0.5,        // optional, default 0.5 seconds
        "force_recompute": false  // optional, skip cache if true
    }

    Response:
    {
        "fen": "...",
        "best_move": "e2e4",
        "score_cp": 20,           // centipawn score (null if mate)
        "score_mate": null,       // mate in N (null if not mate)
        "depth": 20,
        "pv": "e2e4 e7e5 g1f3",
        "cached": true,
        "created_at": "2026-02-21T12:00:00"  // only if cached
    }
    """
    try:
        from app.backend.services.analyzer_service import analyze_position

        data = await request.json()
        fen = data.get("fen", "").strip()
        depth = int(data.get("depth", 20))
        time_limit = float(data.get("time_limit", 0.5))
        force_recompute = bool(data.get("force_recompute", False))

        if not fen:
            raise HTTPException(status_code=400, detail="FEN is required")

        result = await analyze_position(
            fen=fen,
            depth=depth,
            time_limit=time_limit,
            force_recompute=force_recompute
        )

        if "error" in result:
            logger.error(f"Analysis error: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /analyze endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/games/{game_id}/analyze")
async def batch_analyze_game(game_id: int, request: Request):
    """
    Batch analyze all positions (FENs) from an uploaded game.

    This endpoint:
    1. Fetches all moves from the game
    2. Analyzes each FEN with Stockfish
    3. Stores evaluations in the evals table
    4. Returns progress/results

    Query parameters (optional):
    - depth: Search depth (default 20)
    - time_limit: Time per position in seconds (default 0.5)

    Request body (optional):
    {
        "depth": 20,
        "time_limit": 0.5
    }

    Response:
    {
        "success": true,
        "game_id": 1,
        "total_positions": 50,
        "analyzed": 45,
        "cached": 5,
        "errors": 0,
        "total_time_seconds": 12.5,
        "message": "Analyzed 45 new positions, 5 from cache"
    }
    """
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not configured.")

    try:
        from app.backend.services.analyzer_service import analyze_position

        # Get parameters from body or query
        try:
            body = await request.json()
            depth = int(body.get("depth", 20))
            time_limit = float(body.get("time_limit", 0.5))
        except Exception:
            # Try query params if no body
            depth = 20
            time_limit = 0.5

        # Fetch all moves for this game
        rows = await get_moves(game_id)
        if not rows:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found or has no moves")

        logger.info(f"Batch analyzing {len(rows)} positions for game {game_id}")

        analyzed_count = 0
        cached_count = 0
        error_count = 0
        import time
        start_time = time.time()

        # Analyze each position
        for row in rows:
            fen = row.get("fen")
            if not fen:
                continue

            try:
                result = await analyze_position(
                    fen=fen,
                    depth=depth,
                    time_limit=time_limit,
                    force_recompute=False  # Use cache if available
                )

                if "error" not in result:
                    if result.get("cached"):
                        cached_count += 1
                    else:
                        analyzed_count += 1
                    logger.debug(f"Analyzed FEN: {fen[:30]}...")
                else:
                    error_count += 1
                    logger.warning(f"Error analyzing FEN: {result.get('error')}")

            except Exception as e:
                error_count += 1
                logger.error(f"Exception analyzing FEN: {e}")

        elapsed = time.time() - start_time

        logger.info(
            f"Batch analysis complete: analyzed={analyzed_count}, cached={cached_count}, errors={error_count}, time={elapsed:.2f}s"
        )

        return {
            "success": True,
            "game_id": game_id,
            "total_positions": len(rows),
            "analyzed": analyzed_count,
            "cached": cached_count,
            "errors": error_count,
            "total_time_seconds": round(elapsed, 2),
            "message": f"Analyzed {analyzed_count} new positions, {cached_count} from cache"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")
