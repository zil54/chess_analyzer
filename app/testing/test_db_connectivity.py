# Games/chess_analyzer/testing/test_db_connectivity.py
import pytest


@pytest.mark.asyncio
async def test_can_connect_and_upsert_into_evals(db_conn):
    # Use a deterministic FEN (starting position)
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    payload = {
        "fen": fen,
        "best_move": "e2e4",
        "score_cp": 20,
        "score_mate": None,
        "depth": 12,
        "pv": "e2e4 e7e5 g1f3",
    }

    # Upsert into existing evals table. Assumes schema:
    # evals(fen TEXT PRIMARY KEY, best_move TEXT, score_cp INT, score_mate INT, depth INT, pv TEXT, created_at TIMESTAMP DEFAULT NOW())
    async with db_conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO evals (fen, best_move, score_cp, score_mate, depth, pv)
            VALUES (%(fen)s, %(best_move)s, %(score_cp)s, %(score_mate)s, %(depth)s, %(pv)s)
            ON CONFLICT (fen) DO UPDATE SET
                best_move = EXCLUDED.best_move,
                score_cp = EXCLUDED.score_cp,
                score_mate = EXCLUDED.score_mate,
                depth = EXCLUDED.depth,
                pv = EXCLUDED.pv,
                created_at = NOW()
            """,
            payload,
        )
        await db_conn.commit()

    async with db_conn.cursor() as cur:
        await cur.execute(
            """
            SELECT fen, best_move, score_cp, score_mate, depth, pv
            FROM evals
            WHERE fen = %s
            """,
            (fen,),
        )
        row = await cur.fetchone()

    assert row is not None
    assert row["fen"] == fen
    assert row["best_move"] == payload["best_move"]
    assert row["score_cp"] == payload["score_cp"]
    assert row["score_mate"] == payload["score_mate"]
    assert row["depth"] == payload["depth"]
    assert row["pv"] == payload["pv"]
