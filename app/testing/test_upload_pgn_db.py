import pytest


@pytest.mark.asyncio
async def test_create_game_endpoint_writes_games_and_moves() -> None:
    """Integration-ish test: call POST /games and verify rows exist in games and moves."""

    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = """[Event \"Test\"]
[Site \"Local\"]
[Date \"2026.02.21\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 1-0
"""

    with TestClient(app) as client:
        files = {"file": ("game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")}
        resp = client.post("/games", files=files)
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["success"] is True
        gid = payload["id"]

    from app.backend.db.db import get_connection

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, white, black, result, event, site, date, raw_pgn FROM public.games WHERE id=%s",
                (gid,),
            )
            game_row = await cur.fetchone()
            assert game_row is not None
            assert game_row["white"] == "WhitePlayer"
            assert game_row["black"] == "BlackPlayer"
            assert game_row["result"] == "1-0"

            await cur.execute("SELECT COUNT(*) AS n FROM public.moves WHERE game_id=%s", (gid,))
            n = (await cur.fetchone())["n"]
            assert n == 5


def test_fetch_game_moves_returns_movetext_with_variations_from_stored_pgn() -> None:
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = """[Event \"Variation Test\"]
[Site \"Local\"]
[Date \"2026.02.21\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 (1. d4 d5 2. c4) e5 2. Nf3 Nc6 1-0
"""

    with TestClient(app) as client:
        create_resp = client.post(
            "/games",
            files={"file": ("variation-game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        moves_resp = client.get(f"/games/{game_id}/moves")

    assert moves_resp.status_code == 200, moves_resp.text
    payload = moves_resp.json()
    assert payload["movetext"].endswith("1-0")
    assert "e4" in payload["movetext"]
    assert "d4" in payload["movetext"]
    assert "(" in payload["movetext"]
    assert ")" in payload["movetext"]
    assert payload["variation_tree"]["id"] == 0
    assert payload["mainline_node_ids"] == [0, 1, 2, 3, 4]

    side_variation = next(node for node in payload["variation_tree"]["variations"] if node["san"] == "d4")
    assert side_variation["is_mainline"] is False
    assert side_variation["anchor_mainline_index"] == 0


def test_fetch_game_moves_rehydrates_nag_symbols_from_stored_raw_pgn() -> None:
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = """[Event \"NAG Test\"]
[Site \"Local\"]
[Date \"2026.02.21\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 $14 e5 $19 2. Nf3 $1 Nc6 $2 1-0
"""

    with TestClient(app) as client:
        create_resp = client.post(
            "/games",
            files={"file": ("nag-game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        moves_resp = client.get(f"/games/{game_id}/moves")

    assert moves_resp.status_code == 200, moves_resp.text
    payload = moves_resp.json()
    assert "$14" not in payload["movetext"]
    assert "$19" not in payload["movetext"]
    assert "e4 +=" in payload["movetext"]
    assert "e5 -+" in payload["movetext"]

    e4_node = payload["variation_tree"]["variations"][0]
    e5_node = e4_node["variations"][0]
    assert e4_node["nag_display"] == "+="
    assert e5_node["nag_display"] == "-+"
    assert payload["positions"][1]["nag_display"] == "+="
    assert payload["positions"][2]["nag_display"] == "-+"


