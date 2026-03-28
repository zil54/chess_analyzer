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

VALID_PGN_WITH_VARIATIONS = """[Event \"Variation Test\"]
[Site \"Local\"]
[Date \"2026.03.10\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 (1. d4 d5 2. c4) e5 2. Nf3 Nc6 1-0
"""

INVALID_PGN = "not a real pgn"


def _flatten_tree(node: dict | None) -> list[dict]:
    if not node:
        return []

    nodes = [node]
    for child in node.get("variations", []) or []:
        nodes.extend(_flatten_tree(child))
    return nodes


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
    assert payload["movetext"] == "1. e4 e5 2. Nf3 Nc6 1-0"
    assert payload["mainline_node_ids"] == [0, 1, 2, 3, 4]
    assert payload["variation_tree"]["id"] == 0


def test_post_games_returns_full_movetext_with_variations_without_db(monkeypatch) -> None:
    monkeypatch.setattr(routes, "DB_ENABLED", False)

    with TestClient(app) as client:
        resp = client.post(
            "/games",
            files={"file": ("variation-game.pgn", VALID_PGN_WITH_VARIATIONS.encode("utf-8"), "application/x-chess-pgn")},
        )

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["success"] is True
    assert payload["movetext"].endswith("1-0")
    assert "e4" in payload["movetext"]
    assert "d4" in payload["movetext"]
    assert "(" in payload["movetext"]
    assert ")" in payload["movetext"]

    tree_nodes = _flatten_tree(payload["variation_tree"])
    sans = {node.get("san") for node in tree_nodes if node.get("san")}
    assert {"e4", "e5", "Nf3", "Nc6", "d4", "d5", "c4"}.issubset(sans)
    assert payload["mainline_node_ids"] == [0, 1, 2, 3, 4]

    side_variation = next(node for node in payload["variation_tree"]["variations"] if node["san"] == "d4")
    assert side_variation["is_mainline"] is False
    assert side_variation["anchor_mainline_index"] == 0


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

