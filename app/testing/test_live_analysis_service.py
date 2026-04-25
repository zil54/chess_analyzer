from typing import cast

from app.backend.services.live_analysis_service import parse_stockfish_line
def test_parse_stockfish_line_parses_centipawn_eval() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    line = "info depth 20 seldepth 30 multipv 2 score cp 25 nodes 123456 pv e2e4 e7e5 g1f3"
    parsed = parse_stockfish_line(fen, line)
    assert parsed == {
        "fen": fen,
        "depth": 20,
        "multipv": 2,
        "score_cp": 25,
        "best_move": "e2e4",
        "pv": "e2e4 e7e5 g1f3",
    }
def test_parse_stockfish_line_parses_mate_eval_and_truncates_pv() -> None:
    fen = "8/8/8/8/8/8/8/K6k w - - 0 1"
    moves = "a1a2 h1h2 a2a3 h2h3 a3a4 h3h4 a4a5 h4h5 a5a6 h5h6 a6a7"
    line = f"info depth 18 multipv 1 score mate 3 nodes 42 pv {moves}"
    parsed = parse_stockfish_line(fen, line)
    assert parsed["fen"] == fen
    assert parsed["depth"] == 18
    assert parsed["multipv"] == 1
    assert parsed["score_mate"] == 3
    assert parsed["best_move"] == "a1a2"
    pv = cast(str, parsed["pv"])
    assert len(pv.split()) == 10


def test_parse_stockfish_line_normalizes_black_to_move_score_to_white_perspective() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    line = "info depth 20 multipv 1 score cp 100 nodes 123 pv e7e5"
    parsed = parse_stockfish_line(fen, line)
    assert parsed["score_cp"] == -100


