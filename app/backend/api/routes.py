from fastapi import APIRouter, HTTPException, Request, Response
import chess
import chess.pgn
import chess.svg
import io
import re

try:
    from app.backend.db.db import (
        create_game,
        insert_moves,
        get_moves,
        get_game_raw_pgn,
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

NAG_DISPLAY_MAP = {
    1: "!",
    2: "?",
    3: "!!",
    4: "??",
    5: "!?",
    6: "?!",
    10: "=",
    11: "=",
    12: "∞",
    13: "∞",
    14: "+=",
    15: "=+",
    16: "+/-",
    17: "-/+",
    18: "+-",
    19: "-+",
    20: "+-",
    21: "-+",
    22: "⩲",
    23: "⩱",
    24: "±",
    25: "∓",
    26: "+-",
    27: "-+",
    32: "⟳",
    36: "↑",
    40: "→",
    44: "⇄",
    132: "⟳",
    136: "↑",
    140: "∆",
    142: "⌓",
    145: "RR",
    146: "N",
}

COMMENT_ASSESSMENT_ALIAS_MAP = {
    "1/2-1/2": "=",
    "½-½": "=",
    "=": "=",
    "∞": "∞",
    "+=": "+=",
    "=+": "=+",
    "+/-": "+/-",
    "-/+": "-/+",
    "+-": "+-",
    "-+": "-+",
    "++-": "+-",
    "--+": "-+",
    "+--": "+-",
    "-++": "-+",
}

PURE_EVAL_COMMENT_REGEX = re.compile(
    r"^\s*\[%eval\s(?:(?P<mate>#[+-]?\d+)|(?P<cp>[+-]?(?:\d+(?:\.\d+)?|\.\d+)))(?:,(?P<depth>\d+))?\]\s*$"
)

MOVETEXT_PURE_EVAL_COMMENT_REGEX = re.compile(
    r"\{\s*\[%eval\s(?:(?P<mate>#[+-]?\d+)|(?P<cp>[+-]?(?:\d+(?:\.\d+)?|\.\d+)))(?:,(?P<depth>\d+))?\]\s*\}"
)

MOVETEXT_COMMENT_ALIAS_REGEX = re.compile(
    r"\{\s*(?P<alias>1/2-1/2|½-½|=|∞|\+=|=\+|\+/-|-/\+|\+-|-\+)\s*\}"
)


async def _read_pgn_from_request(request: Request) -> str:
    """Read PGN text from JSON or multipart form-data."""
    try:
        data = await request.json()
        pgn_str = (data.get("pgn") or "").strip()
    except Exception:
        try:
            form = await request.form()
            file = form.get("file")
            if file is None:
                pgn_str = (form.get("pgn") or "").strip()
            else:
                try:
                    pgn_bytes = await file.read()
                except Exception:
                    pgn_bytes = file.file.read() if getattr(file, "file", None) else b""

                if not pgn_bytes:
                    raise HTTPException(status_code=400, detail="Uploaded PGN file is empty")

                try:
                    pgn_str = pgn_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    pgn_str = pgn_bytes.decode("latin-1")

                pgn_str = pgn_str.strip()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PGN: {str(e)}")

    if not pgn_str:
        raise HTTPException(status_code=400, detail="PGN data is required")

    return pgn_str


def _read_pgn_game(pgn_str: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(io.StringIO(pgn_str))
    if not game:
        raise ValueError("No valid game found in PGN")

    game_errors = getattr(game, "errors", None) or []
    if game_errors:
        raise ValueError(str(game_errors[0]))

    return game


def _nag_symbols(nags: set[int] | list[int] | tuple[int, ...] | None) -> list[str]:
    ordered_nags = sorted({int(nag) for nag in (nags or [])})
    return [NAG_DISPLAY_MAP.get(nag, f"${nag}") for nag in ordered_nags]


def _nag_display(nags: set[int] | list[int] | tuple[int, ...] | None) -> str | None:
    symbols = _nag_symbols(nags)
    return " ".join(symbols) if symbols else None


def _assessment_display_from_eval(cp: float | None = None, mate: int | None = None) -> str | None:
    if mate is not None:
        if mate > 0:
            return "+-"
        if mate < 0:
            return "-+"
        return "="

    if cp is None:
        return None

    if abs(cp) < 0.15:
        return "="
    if abs(cp) < 0.60:
        return "+=" if cp > 0 else "=+"
    if abs(cp) < 1.50:
        return "+/-" if cp > 0 else "-/+"
    return "+-" if cp > 0 else "-+"


def _assessment_from_comment(comment: str | None) -> tuple[str | None, str | None]:
    if comment is None:
        return None, None

    stripped = comment.strip()
    if not stripped:
        return None, None

    alias_display = COMMENT_ASSESSMENT_ALIAS_MAP.get(stripped)
    if alias_display:
        return alias_display, None

    match = PURE_EVAL_COMMENT_REGEX.fullmatch(stripped)
    if not match:
        return None, comment

    mate_group = match.group("mate")
    cp_group = match.group("cp")
    mate_value = int(mate_group[1:]) if mate_group else None
    cp_value = float(cp_group) if cp_group is not None else None
    return _assessment_display_from_eval(cp=cp_value, mate=mate_value), None


def _replace_numeric_nags_with_symbols(movetext: str) -> str:
    return re.sub(
        r"\$(\d+)",
        lambda match: NAG_DISPLAY_MAP.get(int(match.group(1)), match.group(0)),
        movetext,
    )


def _replace_assessment_comments_with_symbols(movetext: str) -> str:
    def replace_eval_comment(match: re.Match[str]) -> str:
        mate_group = match.group("mate")
        cp_group = match.group("cp")
        mate_value = int(mate_group[1:]) if mate_group else None
        cp_value = float(cp_group) if cp_group is not None else None
        display = _assessment_display_from_eval(cp=cp_value, mate=mate_value)
        return display or match.group(0)

    movetext = MOVETEXT_PURE_EVAL_COMMENT_REGEX.sub(replace_eval_comment, movetext)
    return MOVETEXT_COMMENT_ALIAS_REGEX.sub(
        lambda match: COMMENT_ASSESSMENT_ALIAS_MAP.get(match.group("alias"), match.group(0)),
        movetext,
    )


def _annotate_position_from_node(position: dict, node: chess.pgn.GameNode | dict | None) -> dict:
    if not position:
        return position

    if isinstance(node, dict):
        nags = list(node.get("nags") or [])
        nag_symbols = list(node.get("nag_symbols") or [])
        nag_display = node.get("nag_display")
        comment = node.get("comment")
    else:
        raw_nags = getattr(node, "nags", set()) or set()
        nags = sorted(int(nag) for nag in raw_nags)
        nag_symbols = _nag_symbols(raw_nags)
        nag_display = _nag_display(raw_nags)
        comment = (getattr(node, "comment", None) or None)

    derived_display, normalized_comment = _assessment_from_comment(comment)
    if nag_display is None:
        nag_display = derived_display
        if derived_display and not nag_symbols:
            nag_symbols = [derived_display]

    position["nags"] = nags
    position["nag_symbols"] = nag_symbols
    position["nag_display"] = nag_display
    if comment is not None or normalized_comment is None:
        position["comment"] = normalized_comment
    return position


def _build_mainline_node_lookup(variation_tree: dict | None) -> dict[int, dict]:
    if not variation_tree:
        return {}

    lookup: dict[int, dict] = {0: variation_tree}
    node = variation_tree
    while node:
        variations = [variation for variation in (node.get("variations") or []) if isinstance(variation, dict)]
        mainline_child = next((variation for variation in variations if variation.get("is_mainline")), None)
        if not mainline_child:
            break
        lookup[int(mainline_child.get("ply", 0))] = mainline_child
        node = mainline_child

    return lookup


def _export_pgn_movetext(game: chess.pgn.Game) -> str:
    exporter = chess.pgn.StringExporter(
        headers=False,
        comments=True,
        variations=True,
        columns=None,
    )
    movetext = game.accept(exporter).strip()
    movetext = _replace_numeric_nags_with_symbols(movetext)
    return _replace_assessment_comments_with_symbols(movetext)


def _extract_pgn_movetext(pgn_str: str) -> str:
    try:
        return _export_pgn_movetext(_read_pgn_game(pgn_str))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(str(e))


def _build_variation_tree(game: chess.pgn.Game) -> tuple[dict, list[int]]:
    board = game.board()
    next_node_id = 1
    mainline_node_ids = [0]

    root = {
        "id": 0,
        "ply": 0,
        "move_number": 0,
        "color": None,
        "move": None,
        "san": None,
        "fen": board.fen(),
        "comment": (game.comment or None) if getattr(game, "comment", None) else None,
        "starting_comment": None,
        "nags": [],
        "nag_symbols": [],
        "nag_display": None,
        "is_mainline": True,
        "mainline_index": 0,
        "anchor_mainline_index": 0,
        "variations": [],
    }

    def build_children(
        pgn_node: chess.pgn.GameNode,
        current_board: chess.Board,
        parent_ply: int,
        parent_mainline_index: int,
        follows_mainline: bool,
    ) -> list[dict]:
        nonlocal next_node_id

        children: list[dict] = []
        for variation_index, child in enumerate(pgn_node.variations):
            move = child.move
            san = current_board.san(move)
            move_number = current_board.fullmove_number
            color = "w" if current_board.turn == chess.WHITE else "b"

            child_board = current_board.copy(stack=False)
            child_board.push(move)

            is_mainline = follows_mainline and variation_index == 0
            node_id = next_node_id
            next_node_id += 1

            mainline_index = (parent_mainline_index + 1) if is_mainline else None
            anchor_mainline_index = parent_mainline_index
            if is_mainline and mainline_index is not None:
                anchor_mainline_index = mainline_index
                mainline_node_ids.append(node_id)

            node = {
                "id": node_id,
                "ply": parent_ply + 1,
                "move_number": move_number,
                "color": color,
                "move": move.uci(),
                "san": san,
                "fen": child_board.fen(),
                "comment": (child.comment or None) if getattr(child, "comment", None) else None,
                "starting_comment": (getattr(child, "starting_comment", None) or None),
                "nags": sorted(int(nag) for nag in (getattr(child, "nags", set()) or set())),
                "nag_symbols": _nag_symbols(getattr(child, "nags", set()) or set()),
                "nag_display": _nag_display(getattr(child, "nags", set()) or set()),
                "is_mainline": is_mainline,
                "mainline_index": mainline_index,
                "anchor_mainline_index": anchor_mainline_index,
                "variations": [],
            }
            _annotate_position_from_node(node, child)
            node["variations"] = build_children(
                child,
                child_board,
                node["ply"],
                mainline_index if mainline_index is not None else anchor_mainline_index,
                is_mainline,
            )
            children.append(node)

        return children

    root["variations"] = build_children(game, board, 0, 0, True)
    return root, mainline_node_ids


def _extract_pgn_tree(pgn_str: str) -> tuple[dict, list[int]]:
    try:
        return _build_variation_tree(_read_pgn_game(pgn_str))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(str(e))


def _parse_pgn_payload(pgn_str: str) -> tuple[dict, list[dict], list[dict], int, str, dict, list[int]]:
    """Parse PGN into headers, UI positions, DB move rows, ply count, movetext, and variation tree."""
    try:
        game = _read_pgn_game(pgn_str)

        headers = {
            "event": game.headers.get("Event", "Unknown"),
            "white": game.headers.get("White", "Unknown"),
            "black": game.headers.get("Black", "Unknown"),
            "date": game.headers.get("Date", "Unknown"),
            "result": game.headers.get("Result", "*"),
            "site": game.headers.get("Site", "Unknown"),
        }

        board = game.board()
        positions = [{
            "move_number": 0,
            "fen": board.fen(),
            "move": None,
            "san": None,
        }]
        move_rows = [{
            "ply": 0,
            "san": "START",
            "fen": board.fen(),
            "comment": None,
            "cp_tag": False,
        }]

        ply = 0
        node = game
        for move in game.mainline_moves():
            ply += 1
            san = board.san(move)
            board.push(move)

            try:
                node = node.variation(move)
                comment = (node.comment or None) if node else None
            except Exception:
                node = None
                comment = None

            positions.append({
                "move_number": board.fullmove_number,
                "fen": board.fen(),
                "move": move.uci(),
                "san": san,
            })
            _annotate_position_from_node(positions[-1], node)
            move_rows.append({
                "ply": ply,
                "san": san,
                "fen": board.fen(),
                "comment": comment,
                "cp_tag": False,
            })
            _annotate_position_from_node(move_rows[-1], node)

        if ply == 0:
            raise ValueError("PGN must contain at least one legal move")

        variation_tree, mainline_node_ids = _build_variation_tree(game)
        return headers, positions, move_rows, ply, _export_pgn_movetext(game), variation_tree, mainline_node_ids
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(str(e))


@router.post("/analyze_pgn")
async def analyze_pgn(request: Request):
    """
    Parse a PGN and return all positions.
    If DB_ENABLED, also persist the game and moves to the database.
    Accepts either JSON with {"pgn": "..."} or multipart file upload
    """
    pgn_str = await _read_pgn_from_request(request)

    try:
        headers, positions, move_rows, ply, movetext, variation_tree, mainline_node_ids = _parse_pgn_payload(pgn_str)

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
            "positions": positions,
            "movetext": movetext,
            "variation_tree": variation_tree,
            "mainline_node_ids": mainline_node_ids,
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
    """Create games from uploaded PGN. Supports multiple games.
    """
    logger.info("=== POST /games called ===")
    logger.info(f"DB_ENABLED: {DB_ENABLED}")

    pgn_str = await _read_pgn_from_request(request)
    logger.info(f"Read PGN: {len(pgn_str)} bytes")

    # Split and process all games in the PGN
    pgn_io = io.StringIO(pgn_str)
    created_games = []

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        # Convert back to string for parsing/saving
        game_str = str(game)
        try:
            headers, positions, move_rows, ply, movetext, variation_tree, mainline_node_ids = _parse_pgn_payload(game_str)
            logger.info(f"Parsed {ply} plies from a game in PGN")
        except ValueError as e:
            logger.error(f"Invalid game format in PGN: {e}")
            continue # Skip invalid games

        game_id = None
        if DB_ENABLED:
            try:
                game_id = await create_game(game_str, headers)
                await insert_moves(game_id, move_rows)
            except Exception as e:
                logger.error(f"DB error during insert: {e}", exc_info=True)

        created_games.append({
            "id": game_id,
            "headers": headers,
            "total_moves": ply,
            "positions": positions,
            "movetext": movetext,
            "variation_tree": variation_tree,
            "mainline_node_ids": mainline_node_ids,
        })

    if not created_games:
        raise HTTPException(status_code=400, detail="No valid games found in PGN")

    first_game = created_games[0]
    return {
        "success": True,
        "id": first_game["id"],
        "headers": first_game["headers"],
        "total_moves": first_game["total_moves"],
        "positions": first_game["positions"],
        "movetext": first_game["movetext"],
        "variation_tree": first_game["variation_tree"],
        "mainline_node_ids": first_game["mainline_node_ids"],
        "all_created_ids": [g["id"] for g in created_games if g["id"] is not None],
        "total_games_created": len(created_games)
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

    headers = {}
    movetext = None
    variation_tree = None
    mainline_node_ids = None
    raw_pgn = await get_game_raw_pgn(game_id)
    if raw_pgn:
        try:
            # Extract headers from raw PGN
            headers, _, _, _, movetext_extracted, variation_tree, mainline_node_ids = _parse_pgn_payload(raw_pgn)
            movetext = movetext_extracted
            mainline_lookup = _build_mainline_node_lookup(variation_tree)
            for position in positions:
                _annotate_position_from_node(position, mainline_lookup.get(int(position.get("ply", 0))))
        except ValueError as e:
            logger.warning("Unable to export PGN movetext for game_id=%s: %s", game_id, e)
            # Fallback: try to extract just movetext if full parse fails
            try:
                movetext = _extract_pgn_movetext(raw_pgn)
                variation_tree, mainline_node_ids = _extract_pgn_tree(raw_pgn)
            except:
                pass

    return {
        "success": True,
        "game_id": game_id,
        "headers": headers,
        "total_moves": max(0, len(positions) - 1),
        "positions": positions,
        "movetext": movetext,
        "variation_tree": variation_tree,
        "mainline_node_ids": mainline_node_ids,
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
