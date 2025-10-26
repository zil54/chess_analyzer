import pytest
from chess_analyzer.backend.services.analyzer_service import analyze_position

@pytest.mark.asyncio
async def test_analyze_position_returns_expected():
    # Starting position FEN (standard chess initial setup)
    start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # Call the service function directly
    result = await analyze_position(start_fen)

    # Basic sanity checks
    assert isinstance(result, dict)
    assert result["fen"] == start_fen
    assert "best_move" in result
    assert "evaluation" in result
    assert "depth" in result

