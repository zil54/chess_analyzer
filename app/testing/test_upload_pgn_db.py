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


def test_quiz_endpoint_returns_positions_from_imported_cposition_comments() -> None:
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Quiz Test"]
[Site "Local"]
[Date "2026.04.23"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 e5 2. Nf3 {CPosition} Nc6 *
'''

    with TestClient(app) as client:
        create_resp = client.post(
            "/games",
            files={"file": ("quiz-game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        quiz_resp = client.get(f"/games/{game_id}/quiz")

    assert quiz_resp.status_code == 200, quiz_resp.text
    payload = quiz_resp.json()
    assert payload["success"] is True
    assert len(payload["quiz_positions"]) == 1
    quiz_position = payload["quiz_positions"][0]
    assert quiz_position["ply"] == 4
    assert quiz_position["expected_move_san"] == "Nc6"
    assert quiz_position["color"] == "B"


def test_save_annotations_endpoint_updates_quiz_positions_and_loaded_moves() -> None:
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Annotation Save Test"]
[Site "Local"]
[Date "2026.04.23"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 *
'''

    with TestClient(app) as client:
        create_resp = client.post(
            "/games",
            files={"file": ("annotation-game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        save_resp = client.post(
            f"/games/{game_id}/annotations",
            json={
                "annotations": [
                    {"ply": 3, "comment": "CPosition - test me", "cp_tag": True},
                ]
            },
        )
        assert save_resp.status_code == 200, save_resp.text
        assert save_resp.json()["updated"] == 1

        quiz_resp = client.get(f"/games/{game_id}/quiz")
        moves_resp = client.get(f"/games/{game_id}/moves")

    assert quiz_resp.status_code == 200, quiz_resp.text
    quiz_payload = quiz_resp.json()
    assert len(quiz_payload["quiz_positions"]) == 1
    assert quiz_payload["quiz_positions"][0]["ply"] == 4
    assert quiz_payload["quiz_positions"][0]["expected_move_san"] == "Nc6"
    assert quiz_payload["quiz_positions"][0]["color"] == "B"

    assert moves_resp.status_code == 200, moves_resp.text
    moves_payload = moves_resp.json()
    assert moves_payload["positions"][3]["cp_tag"] is True
    assert moves_payload["positions"][3]["comment"] == "CPosition - test me"
    assert moves_payload["variation_tree"]["variations"][0]["variations"][0]["variations"][0]["comment"] == "CPosition - test me"


def test_quiz_endpoint_can_target_the_already_critical_move_itself() -> None:
    from app.backend.main import app
    from fastapi.testclient import TestClient

    pgn = '''[Event "Already Critical Quiz Test"]
[Site "Local"]
[Date "2026.04.23"]
[Round "-"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]

1. e4 e5 2. Nf3 {CPosition - this was already critical move} Nc6 *
'''

    with TestClient(app) as client:
        create_resp = client.post(
            "/games",
            files={"file": ("already-critical-game.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")},
        )
        assert create_resp.status_code == 200, create_resp.text
        game_id = create_resp.json()["id"]

        quiz_resp = client.get(f"/games/{game_id}/quiz")

    assert quiz_resp.status_code == 200, quiz_resp.text
    payload = quiz_resp.json()
    assert len(payload["quiz_positions"]) == 1
    quiz_position = payload["quiz_positions"][0]
    assert quiz_position["ply"] == 3
    assert quiz_position["expected_move_san"] == "Nf3"
    assert quiz_position["color"] == "W"


