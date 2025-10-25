
import sys
import asyncio
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from typing import Optional


# -------------------------------------------------------------------
# Event loop policy (Windows fix)
# -------------------------------------------------------------------
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Check your .env file.")

# -------------------------------------------------------------------
# Connection helpers
# -------------------------------------------------------------------

async def get_connection():
    """
    Open a new async connection to the database.
    Caller is responsible for closing it.
    Uses dict_row so results come back as dictionaries.
    """
    return await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)


async def init_db():
    """
    Initialize all core tables for the chess analyzer.
    Safe to call at startup; uses IF NOT EXISTS for idempotency.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            # 1. Sessions
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS session (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    pgn TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)

            # 2. Analyses
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis (
                    id SERIAL PRIMARY KEY,
                    session_id INT NOT NULL REFERENCES session(id) ON DELETE CASCADE,
                    move_number INT NOT NULL,
                    fen TEXT NOT NULL,
                    best_eval FLOAT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)

            # 3. Candidate lines (3 per analysis)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS analysis_line (
                    id SERIAL PRIMARY KEY,
                    analysis_id INT NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
                    rank SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 3),
                    depth INT NOT NULL,
                    moves TEXT NOT NULL,
                    eval FLOAT,
                    UNIQUE (analysis_id, rank)
                )
            """)

            # 4. Critical positions
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS critical_position (
                    id SERIAL PRIMARY KEY,
                    session_id INT NOT NULL REFERENCES session(id) ON DELETE CASCADE,
                    move_number INT NOT NULL,
                    fen TEXT NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)

            # 5. (Optional) User feedback
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id SERIAL PRIMARY KEY,
                    session_id INT NOT NULL REFERENCES session(id) ON DELETE CASCADE,
                    analysis_id INT REFERENCES analysis(id) ON DELETE CASCADE,
                    line_rank SMALLINT CHECK (line_rank BETWEEN 1 AND 3),
                    feedback TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)

        await conn.commit()



# -------------------------------------------------------------------
# Example repository‑style helpers
# -------------------------------------------------------------------

async def insert_session(pgn: str, user_id: Optional[str] = None) -> int:
    """
    Insert a new session row (with PGN text and optional user_id) and return its id.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO session (user_id, pgn, status)
                VALUES (%s, %s, 'pending')
                RETURNING id
                """,
                (user_id, pgn),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row["id"]


async def get_session(session_id: int) -> dict | None:
    """
    Fetch a session row by id.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, user_id, pgn, status, created_at
                FROM session
                WHERE id = %s
                """,
                (session_id,),
            )
            return await cur.fetchone()

