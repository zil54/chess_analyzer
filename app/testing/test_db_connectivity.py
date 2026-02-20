# Games/chess_analyzer/testing/test_db_connectivity.py
import pytest

@pytest.mark.asyncio
async def test_can_connect_and_insert(db_conn):
    # Ensure the table exists (idempotent)
    async with db_conn.cursor() as cur:
        await cur.execute("""
            CREATE TABLE IF NOT EXISTS session_analysis (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        await db_conn.commit()

    # Insert a row
    async with db_conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO session_analysis (name) VALUES (%s) RETURNING id",
            ("pytest-demo",)
        )
        row = await cur.fetchone()
        await db_conn.commit()

    # Verify row exists
    async with db_conn.cursor() as cur:
        await cur.execute(
            "SELECT name FROM session_analysis WHERE id = %s",
            (row[0],)
        )
        result = await cur.fetchone()

    assert result[0] == "pytest-demo"