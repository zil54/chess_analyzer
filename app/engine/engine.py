import os
import chess
import chess.engine

def run_stockfish(fen: str, lines: int = 3) -> dict:
    board = chess.Board(fen)

    # Resolve path to sf.exe relative to backend/engine.py
    base_dir = os.path.dirname(os.path.dirname(__file__))  # chess_analyzer/
    stockfish_path = os.path.join(base_dir, "engine", "sf.exe")

    if not os.path.exists(stockfish_path):
        raise FileNotFoundError(f"Stockfish not found at: {stockfish_path}")

    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        info = engine.analyse(board, chess.engine.Limit(time=0.2), multipv=lines)
        variations = []
        for entry in info:
            pv_moves = entry.get("pv", [])
            score = entry["score"].white().score(mate_score=10000)
            san_line = []
            temp_board = board.copy()
            move_number = temp_board.fullmove_number
            is_white = temp_board.turn

            for move in pv_moves:
                if is_white:
                    san_line.append(f"{move_number}. {temp_board.san(move)}")
                else:
                    san_line.append(f"{temp_board.san(move)}")
                temp_board.push(move)

                # Update for next move
                is_white = temp_board.turn
                if is_white:
                    move_number += 1

            variations.append({
                "line": san_line,
                "score": score
            })
        return { "variations": variations }