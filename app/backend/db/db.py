import sys
import asyncio
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from typing import Optional
from uuid import UUID

# -------------------------------------------------------------------
# Windows event loop fix
# -------------------------------------------------------------------
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENABLED = DATABASE_URL is not None

# -------------------------------------------------------------------
# Connection helper
# -------------------------------------------------------------------
async def get_connection():
    if not DB_ENABLED:
        raise RuntimeError("Database is not configured. Set DATABASE_URL in .env file.")
    return await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)

# -------------------------------------------------------------------
# Schema initialization
# -------------------------------------------------------------------
async def init_db():
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS session (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    pgn TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
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
# Session helpers
# -------------------------------------------------------------------
async def create_session(pgn: str, user_id: Optional[str] = None) -> int:
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

async def get_session(session_id: int) -> Optional[dict]:
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

# -------------------------------------------------------------------
# Critical position helpers
# -------------------------------------------------------------------
async def insert_critical_positions(session_id: int, positions: list[tuple[int, str]]):
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO critical_position (session_id, move_number, fen, comment)
                VALUES (%s, %s, %s, %s)
                """,
                [(session_id, move, fen, None) for move, fen in positions]
            )
        await conn.commit()