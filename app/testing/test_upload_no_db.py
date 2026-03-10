from fastapi.testclient import TestClient

from app.backend.main import app
from app.backend.api import routes


VALID_PGN = """[Event \"Test\"]
[Site \"Local\"]
[Date \"2026.03.10\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 1-0
"""

INVALID_PGN = "not a real pgn"


def test_post_games_returns_positions_without_db(monkeypatch) -> None:
    monkeypatch.setattr(routes, "DB_ENABLED", False)

    with TestClient(app) as client:
        resp = client.post(
            "/games",
            files={"file": ("game.pgn", VALID_PGN.encode("utf-8"), "application/x-chess-pgn")},
        )

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["success"] is True
    assert payload["id"] is None
    assert payload["total_moves"] == 4
    assert len(payload["positions"]) == 5
    assert payload["positions"][0]["san"] is None
    assert payload["positions"][1]["san"] == "e4"


def test_post_games_rejects_malformed_pgn_without_db(monkeypatch) -> None:
    monkeypatch.setattr(routes, "DB_ENABLED", False)

    with TestClient(app) as client:
        resp = client.post(
            "/games",
            files={"file": ("bad.pgn", INVALID_PGN.encode("utf-8"), "application/x-chess-pgn")},
        )

    assert resp.status_code == 400, resp.text
    payload = resp.json()
    assert "Invalid PGN format" in payload["detail"]
    assert "at least one legal move" in payload["detail"]


def test_analyze_pgn_rejects_malformed_pgn_without_db(monkeypatch) -> None:
    monkeypatch.setattr(routes, "DB_ENABLED", False)

    with TestClient(app) as client:
        resp = client.post(
            "/analyze_pgn",
            files={"file": ("bad.pgn", INVALID_PGN.encode("utf-8"), "application/x-chess-pgn")},
        )

    assert resp.status_code == 400, resp.text
    payload = resp.json()
    assert "Invalid PGN format" in payload["detail"]

