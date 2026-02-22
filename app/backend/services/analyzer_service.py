"""
Analyzer Service: Chess position analysis with caching

Implements a cache-then-compute pattern:
1. Check if evaluation exists in DB for the FEN
2. If cache hit: return cached evaluation
3. If cache miss: run Stockfish, store result, return it
"""

import os
import chess
import chess.engine
from typing import Dict, Optional
from app.backend.logs.logger import logger

# Try to import DB functions; gracefully degrade if not available
try:
    from app.backend.db.db import get_eval, upsert_eval, DB_ENABLED
except Exception as e:
    logger.warning(f"Could not import DB functions: {e}")
    DB_ENABLED = False

    async def get_eval(fen: str) -> Optional[Dict]:
        return None

    async def upsert_eval(fen: str, **kwargs) -> None:
        pass


def _get_stockfish_path() -> str:
    """Resolve path to Stockfish executable."""
    # Go up 3 levels from services/ to app/
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    stockfish_path = os.path.join(app_dir, "engine", "sf.exe")

    if not os.path.exists(stockfish_path):
        raise FileNotFoundError(f"Stockfish not found at: {stockfish_path}")

    return stockfish_path


def _analyze_with_stockfish(fen: str, depth: int = 20, time_limit: float = 0.5) -> Dict:
    """
    Run Stockfish analysis on a position.

    Args:
        fen: FEN string
        depth: Search depth (default 20)
        time_limit: Time in seconds to search (default 0.5)

    Returns:
        Dict with: best_move, score_cp, score_mate, depth, pv
    """
    try:
        board = chess.Board(fen)
        stockfish_path = _get_stockfish_path()

        logger.info(f"Starting Stockfish analysis: depth={depth}, time={time_limit}s")

        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            # Use both depth and time limits; whichever is reached first
            limit = chess.engine.Limit(time=time_limit, depth=depth)
            info = engine.analyse(board, limit, multipv=1)

            logger.info(f"Stockfish returned: {len(info) if info else 0} infos")

            if not info:
                logger.warning(f"No analysis returned for FEN: {fen}")
                return {}

            entry = info[0]
            pv_moves = entry.get("pv", [])
            score = entry.get("score")

            logger.info(f"PV length: {len(pv_moves)}, Score: {score}")

            # Extract score in centipawns or mate
            score_cp = None
            score_mate = None
            if score:
                if score.is_mate():
                    score_mate = score.mate()
                else:
                    # White's perspective
                    score_cp = score.white().score()

            # Get best move (first move in PV)
            best_move = pv_moves[0].uci() if pv_moves else None

            # Convert PV to UCI string
            pv_str = " ".join(move.uci() for move in pv_moves[:10]) if pv_moves else ""

            # Get actual depth reached
            actual_depth = entry.get("depth", depth)

            logger.info(f"Analysis result: best_move={best_move}, score_cp={score_cp}, depth={actual_depth}")

            return {
                "best_move": best_move,
                "score_cp": score_cp,
                "score_mate": score_mate,
                "depth": actual_depth,
                "pv": pv_str,
            }

    except Exception as e:
        logger.error(f"Stockfish analysis failed for FEN '{fen}': {e}", exc_info=True)
        return {}


async def analyze_position(
    fen: str,
    depth: int = 20,
    time_limit: float = 0.5,
    force_recompute: bool = False
) -> Dict:
    """
    Analyze a single chess position with caching.

    Implements cache-then-compute pattern:
    1. Check DB cache first (if enabled)
    2. If not found or force_recompute=True, run Stockfish
    3. Store result in DB (if enabled)
    4. Return evaluation

    Args:
        fen: FEN string to analyze
        depth: Search depth (default 20)
        time_limit: Time limit in seconds (default 0.5)
        force_recompute: If True, skip cache and always run Stockfish

    Returns:
        Dict with: fen, best_move, score_cp, score_mate, depth, pv, cached
    """

    logger.info(f"Analyzing FEN (depth={depth}, time={time_limit}s, force={force_recompute})")

    # Validate FEN
    try:
        chess.Board(fen)
    except Exception as e:
        logger.error(f"Invalid FEN: {fen} - {e}")
        return {
            "fen": fen,
            "error": f"Invalid FEN: {str(e)}",
            "cached": False
        }

    # Check cache first
    cached_eval = None
    if DB_ENABLED and not force_recompute:
        try:
            cached_eval = await get_eval(fen)
            if cached_eval:
                cached_depth = cached_eval.get('depth', 0)

                # Only use cache if it's at least as deep as requested
                if cached_depth >= depth:
                    logger.info(f"Cache hit for FEN at depth {cached_depth} (requested {depth})")
                    return {
                        "fen": fen,
                        "best_move": cached_eval.get("best_move"),
                        "score_cp": cached_eval.get("score_cp"),
                        "score_mate": cached_eval.get("score_mate"),
                        "depth": cached_eval.get("depth"),
                        "pv": cached_eval.get("pv"),
                        "cached": True
                    }
                else:
                    # Cached is shallower than requested, need deeper analysis
                    logger.info(f"Cache found but too shallow: cached_depth={cached_depth} < requested_depth={depth}, will analyze deeper")
                    cached_eval = None  # Don't use shallow cache
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            logger.warning(f"Error checking cache: {e}")

    # Cache miss or DB disabled: run Stockfish
    logger.info(f"Cache miss or DB disabled, running Stockfish analysis...")
    eval_result = _analyze_with_stockfish(fen, depth=depth, time_limit=time_limit)

    if not eval_result:
        logger.warning(f"Stockfish returned empty result for FEN: {fen[:40]}...")
        return {
            "fen": fen,
            "error": "Stockfish analysis failed",
            "cached": False
        }

    logger.info(f"Stockfish result: best_move={eval_result.get('best_move')}, score_cp={eval_result.get('score_cp')}, depth={eval_result.get('depth')}")

    # Store in DB
    if DB_ENABLED:
        try:
            logger.info(f"Storing evaluation to DB...")
            await upsert_eval(
                fen=fen,
                best_move=eval_result.get("best_move"),
                score_cp=eval_result.get("score_cp"),
                score_mate=eval_result.get("score_mate"),
                depth=eval_result.get("depth"),
                pv=eval_result.get("pv")
            )
            logger.info(f"✓ Stored evaluation in DB for FEN: {fen[:40]}...")
        except Exception as e:
            logger.error(f"Error storing evaluation in DB: {e}", exc_info=True)

    return {
        "fen": fen,
        "best_move": eval_result.get("best_move"),
        "score_cp": eval_result.get("score_cp"),
        "score_mate": eval_result.get("score_mate"),
        "depth": eval_result.get("depth"),
        "pv": eval_result.get("pv"),
        "cached": False
    }