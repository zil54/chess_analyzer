# -*- coding: utf-8 -*-
"""
Quiz Results Service: Evaluate and compare user moves with Stockfish analysis
"""

import chess
import asyncio
from typing import Dict, List, Optional
from app.backend.logs.logger import logger
from app.backend.services.analyzer_service import analyze_position
from app.backend.runtime import get_stockfish_path

# Try to import DB functions; gracefully degrade if not available
try:
    from app.backend.db.db import get_moves, DB_ENABLED
except Exception as e:
    logger.warning(f"Could not import DB functions: {e}")
    DB_ENABLED = False

    async def get_moves(game_id: int):
        return []


def _run_multipv_analysis(fen: str, depth: int, time_limit: float, num_lines: int = 3) -> List[Dict]:
    """
    Run Stockfish with MultiPV to get multiple evaluation lines.
    Returns list of dicts: [{best_move, score_cp, score_mate, pv_san, pv_uci, depth}, ...]
    """
    import chess.engine

    stockfish_path = get_stockfish_path()
    board = chess.Board(fen)

    try:
        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            limit = chess.engine.Limit(time=time_limit, depth=depth)
            info_list = engine.analyse(board, limit, multipv=num_lines)

            lines = []
            for entry in (info_list if isinstance(info_list, list) else [info_list]):
                pv_moves = entry.get("pv", [])
                score = entry.get("score")

                score_cp = None
                score_mate = None
                if score:
                    white_score = score.white()
                    if white_score.is_mate():
                        score_mate = white_score.mate()
                    else:
                        score_cp = white_score.score()

                best_move_uci = pv_moves[0].uci() if pv_moves else None
                best_move_san = None
                pv_san_parts = []
                pv_uci_parts = []

                temp_board = board.copy()
                move_num = temp_board.fullmove_number
                is_white = temp_board.turn == chess.WHITE

                for i, move in enumerate(pv_moves[:8]):  # show up to 8 moves of line
                    try:
                        san = temp_board.san(move)
                        if i == 0:
                            best_move_san = san
                        if is_white:
                            pv_san_parts.append(f"{move_num}. {san}")
                        else:
                            if i == 0:
                                pv_san_parts.append(f"{move_num}...{san}")
                            else:
                                pv_san_parts.append(san)
                        pv_uci_parts.append(move.uci())
                        temp_board.push(move)
                        is_white = temp_board.turn == chess.WHITE
                        if is_white:
                            move_num += 1
                    except Exception:
                        break

                lines.append({
                    "best_move": best_move_uci,
                    "best_move_san": best_move_san,
                    "score_cp": score_cp,
                    "score_mate": score_mate,
                    "depth": entry.get("depth", depth),
                    "pv_san": " ".join(pv_san_parts),
                    "pv_uci": " ".join(pv_uci_parts),
                    "multipv": entry.get("multipv", 1),
                })
            return lines

    except NotImplementedError:
        # Fallback: run single PV via UCI session, return as single line
        from app.backend.services.analyzer_service import _analyze_with_stockfish_session
        result = _analyze_with_stockfish_session(fen, depth, time_limit, stockfish_path)
        if not result:
            return []
        best_san = _get_move_san(fen, result.get("best_move", ""))
        pv_uci = result.get("pv", "")
        pv_san = _convert_pv_uci_to_san(fen, pv_uci) if pv_uci else ""
        return [{
            "best_move": result.get("best_move"),
            "best_move_san": best_san,
            "score_cp": result.get("score_cp"),
            "score_mate": result.get("score_mate"),
            "depth": result.get("depth", depth),
            "pv_san": pv_san,
            "pv_uci": pv_uci,
            "multipv": 1,
        }]


async def _analyze_position_multipv(fen: str, depth: int = 20, time_limit: float = 0.5) -> Dict:
    """
    Analyze a position with MultiPV=3, returning top 3 lines.
    """
    try:
        lines = await asyncio.to_thread(_run_multipv_analysis, fen, depth, time_limit, 3)
    except Exception as e:
        logger.error(f"MultiPV analysis failed: {e}", exc_info=True)
        lines = []

    if not lines:
        return {"error": "Analysis failed", "lines": []}

    # Annotate each line with NAG symbol
    for line in lines:
        line["nag"] = _eval_nag(line.get("score_cp"), line.get("score_mate"))

    top = lines[0]
    return {
        "best_move": top.get("best_move"),
        "best_move_san": top.get("best_move_san"),
        "score_cp": top.get("score_cp"),
        "score_mate": top.get("score_mate"),
        "nag": top.get("nag"),
        "depth": top.get("depth"),
        "lines": lines,
    }


def _analyze_position_after_move_sync(fen: str, move_san: str, depth: int, time_limit: float) -> Optional[float]:
    """
    Make move_san on fen and analyze the resulting position.
    Returns White-perspective eval in centipawns, or None on failure.
    """
    import chess.engine
    try:
        board = chess.Board(fen)
        move = board.parse_san(move_san)
        board.push(move)
        stockfish_path = get_stockfish_path()
        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            limit = chess.engine.Limit(time=min(time_limit, 0.25), depth=min(depth, 14))
            info = engine.analyse(board, limit)
            score = info.get("score") if isinstance(info, dict) else (info[0].get("score") if info else None)
            if score:
                ws = score.white()
                if ws.is_mate():
                    return 30000 if ws.mate() > 0 else -30000
                return ws.score()
    except NotImplementedError:
        pass  # fallback not needed — partial credit will use default
    except Exception as e:
        logger.warning(f"Could not analyze after move {move_san}: {e}")
    return None


def _partial_credit(eval_swing_cp: Optional[float]) -> float:
    """
    Convert eval swing (centipawns) to a credit score from 0.35 to 0.95.
    0 cp  → 0.95  (game move is essentially as good as SF best)
    200+ cp → 0.35  (game move is significantly worse)
    """
    if eval_swing_cp is None:
        return 0.65
    swing = min(abs(eval_swing_cp), 200)
    return round(0.95 - 0.60 * swing / 200, 2)


def _eval_nag(score_cp: Optional[float], score_mate: Optional[int]) -> str:
    """Return standard chess NAG symbol for the given evaluation (White's perspective)."""
    if score_mate is not None:
        return f"#{score_mate}" if score_mate > 0 else f"#-{abs(score_mate)}"
    if score_cp is None:
        return "?"
    cp = score_cp
    if abs(cp) < 25:   return "="
    if 25 <= cp < 100:  return "⩲"
    if -100 < cp <= -25: return "⩱"
    if 100 <= cp < 300:  return "±"
    if -300 < cp <= -100: return "∓"
    if cp >= 300:  return "+−"
    return "−+"


def _format_score(score_cp: Optional[float], score_mate: Optional[int]) -> str:
    """Return a human-readable evaluation string, e.g. '+1.25' or '#3'."""
    if score_mate is not None:
        return f"#{score_mate}" if score_mate > 0 else f"#-{abs(score_mate)}"
    if score_cp is None:
        return "?"
    v = score_cp / 100
    return f"+{v:.2f}" if v >= 0 else f"{v:.2f}"


def _get_move_san(fen: str, uci_move: str) -> str:
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci_move)
        return board.san(move)
    except Exception as e:
        logger.warning(f"Could not convert {uci_move} to SAN: {e}")
        return uci_move


def _convert_pv_uci_to_san(fen: str, pv_uci_str: str) -> str:
    """Convert space-separated UCI PV string to SAN format with move numbering.
    Example: 'b7b5 c4b5 e3a1' -> '1...b5 2. c4 b5 3. e3 a1'"""
    if not pv_uci_str or not pv_uci_str.strip():
        return ""
    try:
        board = chess.Board(fen)
        uci_moves = pv_uci_str.strip().split()
        san_parts = []
        move_num = board.fullmove_number
        is_white = board.turn == chess.WHITE
        move_count = 0

        for uci in uci_moves[:8]:  # Limit to 8 moves for display
            try:
                move = chess.Move.from_uci(uci)
                san = board.san(move)
                move_count += 1

                if is_white:
                    san_parts.append(f"{move_num}. {san}")
                else:
                    if move_count == 1:
                        san_parts.append(f"{move_num}...{san}")
                    else:
                        san_parts.append(san)

                board.push(move)
                is_white = board.turn == chess.WHITE
                if is_white:
                    move_num += 1
            except Exception:
                break

        return " ".join(san_parts)
    except Exception as e:
        logger.warning(f"Could not convert PV to SAN: {e}")
        return pv_uci_str


async def evaluate_quiz_response(
    game_id: int,
    responses: List[Dict],
    depth: int = 20,
    time_limit: float = 0.5
) -> Dict:
    """
    Evaluate quiz responses. Uses MultiPV=3 so all 3 lines are returned.

    Result types:
      - "full"    – user played SF best move (1.0 credit)
      - "partial" – user played game move but not SF best (0.35–0.95 credit based on eval swing)
      - "fail"    – user played neither
    """
    if not responses or not isinstance(responses, list):
        return {"success": False, "error": "responses must be a non-empty list"}

    logger.info(f"Evaluating {len(responses)} quiz responses for game {game_id}")

    results = []
    total_credit = 0.0

    for i, response in enumerate(responses):
        try:
            ply           = response.get("ply")
            fen_before    = response.get("fen_before")
            user_move     = response.get("user_move", "").strip()   # UCI
            game_move_san = response.get("expected_move", "").strip()  # SAN from PGN

            if not fen_before or not user_move:
                logger.warning(f"Response {i} missing fen_before or user_move")
                continue

            # --- MultiPV analysis (3 lines) ---
            sf = await _analyze_position_multipv(fen_before, depth, time_limit)
            if "error" in sf and not sf.get("lines"):
                logger.warning(f"Could not analyze position {i}: {sf.get('error')}")
                continue

            sf_best_uci = sf.get("best_move", "")
            sf_best_san = sf.get("best_move_san", "") or _get_move_san(fen_before, sf_best_uci)
            sf_eval_cp  = sf.get("score_cp")
            sf_eval_mate = sf.get("score_mate")
            sf_nag      = sf.get("nag", _eval_nag(sf_eval_cp, sf_eval_mate))

            user_move_san = _get_move_san(fen_before, user_move)

            # Convert game move SAN → UCI for comparison
            game_move_uci = ""
            try:
                board = chess.Board(fen_before)
                game_move_uci = board.parse_san(game_move_san).uci()
            except Exception:
                pass

            played_sf_best   = bool(sf_best_uci and user_move.lower() == sf_best_uci.lower())
            played_game_move = bool(game_move_uci and user_move.lower() == game_move_uci.lower())
            game_differs_from_sf = bool(
                sf_best_uci and game_move_uci and
                sf_best_uci.lower() != game_move_uci.lower()
            )

            # --- Partial credit calculation ---
            credit = 0.0
            eval_swing_cp = None
            partial_nag   = None

            if played_sf_best:
                credit      = 1.0
                result_type = "full"
            elif played_game_move and game_differs_from_sf:
                # Analyze position AFTER game move to measure the eval swing
                game_eval_after = await asyncio.to_thread(
                    _analyze_position_after_move_sync,
                    fen_before, game_move_san, depth, time_limit
                )
                if sf_eval_cp is not None and game_eval_after is not None:
                    eval_swing_cp = abs(sf_eval_cp - game_eval_after)
                elif sf_eval_mate is not None:
                    # SF has mate; game move must be much worse
                    eval_swing_cp = 200  # conservative max penalty
                credit      = _partial_credit(eval_swing_cp)
                result_type = "partial"
                partial_nag = _eval_nag(
                    game_eval_after,
                    None  # mate score doesn't apply here generally
                )
            elif played_game_move:
                # game move == SF best, so full credit
                credit      = 1.0
                result_type = "full"
            else:
                credit      = 0.0
                result_type = "fail"

            total_credit += credit

            # --- Feedback text ---
            eval_str = _format_score(sf_eval_cp, sf_eval_mate)
            if result_type == "full" and not game_differs_from_sf:
                feedback = f"✓ Correct — {user_move_san} matches both the game and Stockfish's best move."
            elif result_type == "full" and game_differs_from_sf:
                feedback = (
                    f"✓ Excellent — {user_move_san} is Stockfish's best move "
                    f"(stronger than the game move {game_move_san})."
                )
            elif result_type == "partial":
                swing_str = f"{eval_swing_cp:.0f} cp" if eval_swing_cp is not None else "unknown"
                gm_nag = partial_nag or "?"
                feedback = (
                    f"Partial credit ({credit:.2f}) — you played the game move ({game_move_san} {gm_nag}). "
                    f"Stockfish prefers {sf_best_san} {sf_nag}. "
                    f"Eval swing: {swing_str}."
                )
            else:
                feedback = (
                    f"✗ Incorrect — you played {user_move_san}. "
                    f"Game move: {game_move_san}. "
                    f"SF best: {sf_best_san} {sf_nag} ({eval_str})."
                )

            result_entry = {
                "ply": ply,
                "position_fen": fen_before,
                "game_move_san": game_move_san,
                "game_move_uci": game_move_uci,
                "game_differs_from_sf": game_differs_from_sf,
                "user_move": user_move,
                "user_move_san": user_move_san,
                "result_type": result_type,   # "full" | "partial" | "fail"
                "credit": credit,
                "eval_swing_cp": eval_swing_cp,
                "pass": result_type != "fail",
                "played_sf_best": played_sf_best,
                "played_game_move": played_game_move,
                "feedback": feedback,
                "stockfish": {
                    "best_move": sf_best_uci,
                    "best_move_san": sf_best_san,
                    "score_cp": sf_eval_cp,
                    "score_mate": sf_eval_mate,
                    "nag": sf_nag,
                    "score_formatted": eval_str,
                    "depth": sf.get("depth"),
                    "lines": sf.get("lines", []),
                },
            }

            results.append(result_entry)

        except Exception as e:
            logger.error(f"Error evaluating response {i}: {e}", exc_info=True)
            continue

    total    = len(results)
    max_score = float(total) if total > 0 else 1.0
    pct      = int(round(total_credit / max_score * 100))

    full_cnt    = sum(1 for r in results if r["result_type"] == "full")
    partial_cnt = sum(1 for r in results if r["result_type"] == "partial")
    fail_cnt    = sum(1 for r in results if r["result_type"] == "fail")

    logger.info(
        f"Quiz complete: full={full_cnt}, partial={partial_cnt}, fail={fail_cnt} "
        f"credits={total_credit:.2f}/{max_score:.0f} ({pct}%)"
    )

    return {
        "success": True,
        "game_id": game_id,
        "total_questions": total,
        "pass_answers":    full_cnt + partial_cnt,
        "full_answers":    full_cnt,
        "partial_answers": partial_cnt,
        "fail_answers":    fail_cnt,
        "score_percentage": pct,
        "total_credit": round(total_credit, 2),
        "results": results,
    }


