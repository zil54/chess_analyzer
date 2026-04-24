from __future__ import annotations

import re

from app.backend.logs.logger import logger

_DEPTH_RE = re.compile(r"depth (\d+)")
_MULTIPV_RE = re.compile(r"multipv (\d+)")
_CP_RE = re.compile(r"score cp (-?\d+)")
_MATE_RE = re.compile(r"score mate (-?\d+)")
_PV_RE = re.compile(r"\bpv\s+(.+?)(?:\s+$|$)")


def parse_stockfish_line(fen: str, line: str) -> dict[str, object]:
    """Parse a Stockfish info line into a structured evaluation payload."""
    result: dict[str, object] = {"fen": fen}

    try:
        # UCI scores are from the side-to-move perspective.
        # Normalize them to White's perspective so the same advantage keeps the same sign
        # across consecutive plies.
        fen_parts = fen.split()
        side_to_move = fen_parts[1] if len(fen_parts) > 1 else 'w'
        score_multiplier = -1 if side_to_move == 'b' else 1

        depth_match = _DEPTH_RE.search(line)
        if depth_match:
            result["depth"] = int(depth_match.group(1))

        multipv_match = _MULTIPV_RE.search(line)
        if multipv_match:
            result["multipv"] = int(multipv_match.group(1))

        cp_match = _CP_RE.search(line)
        mate_match = _MATE_RE.search(line)
        if cp_match:
            raw_cp = int(cp_match.group(1))
            result["score_cp"] = raw_cp * score_multiplier
        elif mate_match:
            raw_mate = int(mate_match.group(1))
            result["score_mate"] = raw_mate * score_multiplier

        pv_match = _PV_RE.search(line)
        if pv_match:
            moves = pv_match.group(1).strip().split()
            if moves:
                result["best_move"] = moves[0]
                result["pv"] = " ".join(moves[:10])
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.error("Error parsing Stockfish line: %s", exc)

    return result

