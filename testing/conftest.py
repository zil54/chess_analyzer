# testing/conftest.py
import sys
import asyncio
import os

import pytest
import pytest_asyncio
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_ROOT_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
_BACKEND_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(dotenv_path=_ROOT_DOTENV_PATH, override=False)
load_dotenv(dotenv_path=_BACKEND_DOTENV_PATH, override=False)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    pytest.skip("DATABASE_URL is not set; skipping DB-dependent tests.", allow_module_level=True)

@pytest_asyncio.fixture(scope="session")
async def db_conn():
    """
    Provide a shared async connection for the test session.
    """
    async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_schema(db_conn):
    """Ensure required tables exist for tests.

    IMPORTANT: Don't DROP SCHEMA in a dev database.
    """
    async with db_conn.cursor() as cur:
        await cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.games (
                id SERIAL PRIMARY KEY,
                raw_pgn TEXT,
                white TEXT,
                black TEXT,
                result TEXT,
                event TEXT,
                site TEXT,
                date TEXT
            );
            """
        )
        await cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.moves (
                id SERIAL PRIMARY KEY,
                game_id INT REFERENCES public.games(id),
                ply INT NOT NULL,
                san TEXT NOT NULL,
                fen TEXT NOT NULL,
                comment TEXT,
                cp_tag BOOLEAN DEFAULT FALSE,
                color CHAR(1) GENERATED ALWAYS AS (
                    CASE WHEN ply % 2 = 1 THEN 'W' ELSE 'B' END
                ) STORED,
                UNIQUE (game_id, ply)
            );
            """
        )
        await cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.evals (
                fen TEXT PRIMARY KEY,
                best_move TEXT,
                score_cp INT,
                score_mate INT,
                depth INT,
                pv TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        )
        await db_conn.commit()
    yield
