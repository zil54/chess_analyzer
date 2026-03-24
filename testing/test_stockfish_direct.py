#!/usr/bin/env python
"""
Test Stockfish directly to see if it works
"""
import os
import chess
import chess.engine

try:
    stockfish_path = '../app/engine/sf.exe'

    if not os.path.exists(stockfish_path):
        print(f"✗ Stockfish not found at {stockfish_path}")
        exit(1)

    print("=" * 70)
    print("TESTING STOCKFISH DIRECTLY")
    print("=" * 70)
    print()

    print(f"Stockfish path: {stockfish_path}")
    print(f"File exists: {os.path.exists(stockfish_path)}")
    print()

    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board = chess.Board(fen)

    print(f"Testing with FEN: {fen[:50]}...")
    print()

    print("Opening Stockfish engine...")
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        print("✓ Engine opened")

        # Test with different time limits
        for time_limit in [0.1, 0.3, 0.5, 1.0]:
            print(f"\nAnalyzing with time_limit={time_limit}s...")
            limit = chess.engine.Limit(time=time_limit)
            info = engine.analyse(board, limit, multipv=1)

            if info:
                entry = info[0]
                pv = entry.get("pv", [])
                score = entry.get("score")
                depth = entry.get("depth")

                print(f"  ✓ Got analysis:")
                print(f"    Depth: {depth}")
                print(f"    PV: {[m.uci() for m in pv[:3]]}")
                print(f"    Score: {score}")
            else:
                print(f"  ✗ No analysis returned!")

    print()
    print("=" * 70)

except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

