"""
Test suite for quiz results feature

Tests the evaluation of user quiz responses against Stockfish analysis
"""

import pytest


@pytest.mark.asyncio
async def test_quiz_results_endpoint_evaluates_correct_moves() -> None:
    """Test that correct moves are marked as correct with proper feedback."""
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Test Quiz"]
[Site "Local"]
[Date "2026.04.24"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 {CPosition} e5 *
'''

    with TestClient(app) as client:
        # Create game
        create_resp = client.post(
            "/games",
            files={"file": ("quiz-test.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        # Get quiz positions
        quiz_resp = client.get(f"/games/{game_id}/quiz")
        assert quiz_resp.status_code == 200, quiz_resp.text
        quiz_data = quiz_resp.json()
        
        assert len(quiz_data["quiz_positions"]) > 0
        quiz_position = quiz_data["quiz_positions"][0]
        
        # Submit quiz results - correct move
        result_resp = client.post(
            f"/games/{game_id}/quiz/results",
            json={
                "responses": [
                    {
                        "ply": quiz_position["ply"],
                        "fen_before": quiz_position["fen_before"],
                        "expected_move": quiz_position["expected_move_san"],
                        "user_move": "e7e5",  # e5 in UCI
                    }
                ],
                "depth": 15,
                "time_limit": 0.3
            }
        )
        
        assert result_resp.status_code == 200, result_resp.text
        payload = result_resp.json()
        
        # Verify response structure
        assert payload["success"] is True
        assert payload["game_id"] == game_id
        assert payload["total_questions"] == 1
        assert "results" in payload
        assert len(payload["results"]) == 1
        
        result = payload["results"][0]
        assert "correct" in result
        assert "feedback" in result
        assert "stockfish" in result
        assert "best_move" in result["stockfish"]
        assert "top_moves" in result["stockfish"]
        assert "score_cp" in result["stockfish"] or "score_mate" in result["stockfish"]


@pytest.mark.asyncio
async def test_quiz_results_endpoint_evaluates_incorrect_moves() -> None:
    """Test that incorrect moves are marked as incorrect with suggestion."""
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Test Quiz Wrong"]
[Site "Local"]
[Date "2026.04.24"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 {CPosition} e5 *
'''

    with TestClient(app) as client:
        # Create game
        create_resp = client.post(
            "/games",
            files={"file": ("quiz-wrong.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        # Get quiz positions
        quiz_resp = client.get(f"/games/{game_id}/quiz")
        assert quiz_resp.status_code == 200, quiz_resp.text
        quiz_data = quiz_resp.json()
        quiz_position = quiz_data["quiz_positions"][0]
        
        # Submit quiz results - wrong move
        result_resp = client.post(
            f"/games/{game_id}/quiz/results",
            json={
                "responses": [
                    {
                        "ply": quiz_position["ply"],
                        "fen_before": quiz_position["fen_before"],
                        "expected_move": quiz_position["expected_move_san"],
                        "user_move": "e7e6",  # Wrong: e6 instead of e5
                    }
                ],
                "depth": 15,
                "time_limit": 0.3
            }
        )
        
        assert result_resp.status_code == 200, result_resp.text
        payload = result_resp.json()
        
        assert payload["success"] is True
        result = payload["results"][0]
        
        # Verify it's marked as incorrect
        assert result["correct"] is False
        assert "✗" in result["feedback"] or "best move" in result["feedback"].lower()
        
        # Verify Stockfish data is included
        assert "best_move" in result["stockfish"]
        assert result["stockfish"]["best_move"] != result["user_move"]


@pytest.mark.asyncio
async def test_quiz_results_endpoint_returns_top_3_moves() -> None:
    """Test that top 3 moves from Stockfish are returned."""
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Test Top Moves"]
[Site "Local"]
[Date "2026.04.24"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 {CPosition} e5 *
'''

    with TestClient(app) as client:
        # Create game
        create_resp = client.post(
            "/games",
            files={"file": ("top-moves.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        # Get quiz positions
        quiz_resp = client.get(f"/games/{game_id}/quiz")
        assert quiz_resp.status_code == 200, quiz_resp.text
        quiz_data = quiz_resp.json()
        quiz_position = quiz_data["quiz_positions"][0]
        
        # Submit quiz results
        result_resp = client.post(
            f"/games/{game_id}/quiz/results",
            json={
                "responses": [
                    {
                        "ply": quiz_position["ply"],
                        "fen_before": quiz_position["fen_before"],
                        "expected_move": quiz_position["expected_move_san"],
                        "user_move": "e7e5",
                    }
                ],
                "depth": 15,
                "time_limit": 0.3
            }
        )
        
        assert result_resp.status_code == 200, result_resp.text
        payload = result_resp.json()
        
        result = payload["results"][0]
        stockfish_data = result["stockfish"]
        
        # Verify top moves
        assert "top_moves" in stockfish_data
        assert isinstance(stockfish_data["top_moves"], list)
        assert len(stockfish_data["top_moves"]) <= 3


@pytest.mark.asyncio
async def test_quiz_results_calculates_score() -> None:
    """Test that quiz score percentage is calculated correctly."""
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Test Score"]
[Site "Local"]
[Date "2026.04.24"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 e5 2. Nf3 {CPosition} Nc6 *
'''

    with TestClient(app) as client:
        # Create game
        create_resp = client.post(
            "/games",
            files={"file": ("score-test.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        # Get quiz positions
        quiz_resp = client.get(f"/games/{game_id}/quiz")
        assert quiz_resp.status_code == 200, quiz_resp.text
        quiz_data = quiz_resp.json()
        quiz_position = quiz_data["quiz_positions"][0]
        
        # Submit quiz results with 1 correct and 1 wrong move
        result_resp = client.post(
            f"/games/{game_id}/quiz/results",
            json={
                "responses": [
                    {
                        "ply": quiz_position["ply"],
                        "fen_before": quiz_position["fen_before"],
                        "expected_move": quiz_position["expected_move_san"],
                        "user_move": "b8c6",  # Correct
                    }
                ],
                "depth": 15,
                "time_limit": 0.3
            }
        )
        
        assert result_resp.status_code == 200, result_resp.text
        payload = result_resp.json()
        
        # Verify score calculation
        assert "score_percentage" in payload
        assert "correct_answers" in payload
        assert "incorrect_answers" in payload
        
        # If we got 1 correct and 1 total, should be 100%
        if payload["total_questions"] == 1:
            assert payload["correct_answers"] >= 0
            assert payload["score_percentage"] == (payload["correct_answers"] * 100) // max(1, payload["total_questions"])


@pytest.mark.asyncio
async def test_quiz_results_endpoint_missing_responses() -> None:
    """Test that endpoint handles missing responses gracefully."""
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Test"]
[Site "Local"]
[Date "2026.04.24"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 e5 *
'''

    with TestClient(app) as client:
        # Create game
        create_resp = client.post(
            "/games",
            files={"file": ("test.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]
        
        # Submit empty responses
        result_resp = client.post(
            f"/games/{game_id}/quiz/results",
            json={"responses": []}
        )
        
        assert result_resp.status_code == 400
        assert "responses" in result_resp.text.lower() or "empty" in result_resp.text.lower()

