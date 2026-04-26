# testing/conftest.py
import os

import pytest
import pytest_asyncio
import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from app.backend.runtime import configure_windows_event_loop_policy

configure_windows_event_loop_policy()

_ROOT_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
_BACKEND_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(dotenv_path=_ROOT_DOTENV_PATH, override=False)
load_dotenv(dotenv_path=_BACKEND_DOTENV_PATH, override=False)
DATABASE_URL = os.getenv("DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    if DATABASE_URL:
        return

    skip_db = pytest.mark.skip(reason="DATABASE_URL is not set; skipping DB-dependent tests.")
    for item in items:
        path_str = str(getattr(item, "fspath", ""))
        nodeid = getattr(item, "nodeid", "")
        if "no_db" in path_str or "no_db" in nodeid:
            continue
        item.add_marker(skip_db)


@pytest_asyncio.fixture(scope="session")
async def db_conn():
    """
    Provide a shared async connection for the test session.
    """
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is not set; skipping DB-dependent test fixture.")
    async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_schema():
    """Ensure required tables exist for tests.

    IMPORTANT: Don't DROP SCHEMA in a dev database.
    """
    if not DATABASE_URL:
        yield
        return

    async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as db_conn:
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
                    date TEXT,
                    pgn_source TEXT,
                    imported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
                    variation_parent_id BIGINT,
                    variation_index INT,
                    is_mainline BOOLEAN,
                    move_number INT,
                    fen_before TEXT,
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
                    created_at TIMESTAMP DEFAULT NOW(),
                    engine TEXT,
                    is_tablebase BOOLEAN,
                    game_id BIGINT
                );
                """
            )
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.analysis_lines (
                    fen TEXT NOT NULL,
                    depth INT NOT NULL,
                    line_number INT NOT NULL,
                    best_move TEXT,
                    score_cp INT,
                    score_mate INT,
                    pv TEXT,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (fen, depth, line_number),
                    FOREIGN KEY (fen) REFERENCES public.evals(fen)
                );
                """
            )
            await db_conn.commit()
    yield
