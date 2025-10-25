# Games/chess_analyzer/backend/db/repo.py
from typing import Optional
from chess_analyzer.backend.db.core import get_connection

# -------------------------------------------------------------------
# Session CRUD
# -------------------------------------------------------------------

async def create_session(name: str) -> int:
    """
    Insert a new session row and return its id.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO session_analysis (name) VALUES (%s) RETURNING id",
                (name,),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row["id"]


async def get_session(session_id: int) -> Optional[dict]:
    """
    Fetch a session row by id.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, created_at FROM session_analysis WHERE id = %s",
                (session_id,),
            )
            return await cur.fetchone()


async def get_latest_lines(limit: int = 10) -> list[dict]:
    """
    Fetch the most recent sessions.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, created_at FROM session_analysis "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return await cur.fetchall()


async def get_history() -> list[dict]:
    """
    Fetch all sessions in chronological order.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name, created_at FROM session_analysis ORDER BY id"
            )
            return await cur.fetchall()