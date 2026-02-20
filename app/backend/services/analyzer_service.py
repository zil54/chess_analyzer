# backend/services/analyzer.py

from typing import Dict

# Stub implementation — later you can wire in python-chess + Stockfish
async def analyze_position(fen: str) -> Dict:
    """
    Analyze a single chess position given as FEN.
    Returns a dict with dummy evaluation data for now.
    """

    return {
        "fen": fen,
        "best_move": "a6",     # placeholder
        "evaluation": 0.0,     # centipawn score placeholder
        "depth": 12            # pretend search depth
    }