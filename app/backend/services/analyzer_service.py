# -*- coding: utf-8 -*-
"""
Analyzer Service: Chess position analysis with caching

Implements a cache-then-compute pattern:
1. Check if evaluation exists in DB for the FEN
2. If cache hit: return cached evaluation
3. If cache miss: run Stockfish, store result, return it
"""

import asyncio
import chess
import chess.engine
from typing import Dict, Optional
from app.backend.logs.logger import logger
from app.backend.runtime import get_stockfish_path
from app.backend.services.stockfish_parser import parse_stockfish_line
from app.engine.stockfish_session import StockfishSession

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


def _normalize_analysis_result(raw_result: Dict, requested_depth: int) -> Dict:
    return {
        "best_move": raw_result.get("best_move"),
        "score_cp": raw_result.get("score_cp"),
        "score_mate": raw_result.get("score_mate"),
        "depth": raw_result.get("depth", requested_depth),
        "pv": raw_result.get("pv", ""),
    }



def _build_go_command(depth: int, time_limit: float) -> str:
    command = ["go", "depth", str(max(1, int(depth)))]
    if time_limit and time_limit > 0:
        command.extend(["movetime", str(max(1, int(time_limit * 1000)))])
    return " ".join(command)



def _analyze_with_simple_engine(fen: str, depth: int, time_limit: float, stockfish_path: str) -> Dict:
    board = chess.Board(fen)

    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
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

        score_cp = None
        score_mate = None
        if score:
            white_score = score.white()
            if white_score.is_mate():
                score_mate = white_score.mate()
            else:
                score_cp = white_score.score()

        best_move = pv_moves[0].uci() if pv_moves else None
        pv_str = " ".join(move.uci() for move in pv_moves[:10]) if pv_moves else ""
        actual_depth = entry.get("depth", depth)

        logger.info(f"Analysis result: best_move={best_move}, score_cp={score_cp}, depth={actual_depth}")

        return {
            "best_move": best_move,
            "score_cp": score_cp,
            "score_mate": score_mate,
            "depth": actual_depth,
            "pv": pv_str,
        }



def _analyze_with_stockfish_session(fen: str, depth: int, time_limit: float, stockfish_path: str) -> Dict:
    session = StockfishSession(stockfish_path)
    latest_result: Dict = {}

    try:
        session.send("uci")
        session.send("isready")
        for line in session.read_lines():
            if line == "readyok":
                break

        session.send("ucinewgame")
        session.send("setoption name UCI_AnalyseMode value true")
        session.send("setoption name MultiPV value 1")
        session.send(f"position fen {fen}")
        session.send(_build_go_command(depth, time_limit))

        for line in session.read_lines():
            if line.startswith("bestmove"):
                break

            parsed = parse_stockfish_line(fen, line)
            if parsed.get("pv"):
                latest_result = parsed

        if latest_result:
            normalized = _normalize_analysis_result(latest_result, depth)
            logger.info(
                "Fallback Stockfish session result: best_move=%s, score_cp=%s, depth=%s",
                normalized.get("best_move"),
                normalized.get("score_cp"),
                normalized.get("depth"),
            )
            return normalized

        logger.warning("Fallback Stockfish session produced no PV for FEN: %s", fen)
        return {}
    finally:
        try:
            session.send("stop")
        except Exception:
            pass
        try:
            session.send("quit")
        except Exception:
            pass
        try:
            if session.process.poll() is None:
                session.process.terminate()
                session.process.wait(timeout=2)
        except Exception:
            try:
                session.process.kill()
            except Exception:
                pass



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
        chess.Board(fen)
        stockfish_path = get_stockfish_path()

        logger.info(f"Starting Stockfish analysis: depth={depth}, time={time_limit}s")

        try:
            return _analyze_with_simple_engine(fen, depth, time_limit, stockfish_path)
        except NotImplementedError:
            logger.warning(
                "python-chess engine launch is not supported in this runtime; falling back to direct UCI session"
            )
            return _analyze_with_stockfish_session(fen, depth, time_limit, stockfish_path)
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
    eval_result = await asyncio.to_thread(_analyze_with_stockfish, fen, depth, time_limit)

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
            logger.info("[OK] Stored evaluation in DB for FEN: %s...", fen[:40])
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
