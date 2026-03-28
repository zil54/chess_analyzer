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
