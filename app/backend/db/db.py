import sys
import asyncio
import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Any

# -------------------------------------------------------------------
# Windows event loop fix
# -------------------------------------------------------------------
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
_ROOT_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
_BACKEND_DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Load in a few places to handle different working directories (repo root, app/backend, etc.)
load_dotenv(dotenv_path=_ROOT_DOTENV_PATH, override=False)
load_dotenv(dotenv_path=_BACKEND_DOTENV_PATH, override=False)

# Also try discovering .env from the current working directory upward.
try:
    _FOUND_DOTENV = find_dotenv(usecwd=True)
    if _FOUND_DOTENV:
        load_dotenv(dotenv_path=_FOUND_DOTENV, override=False)
except Exception:
    pass


def _build_database_url_from_parts() -> Optional[str]:
    """Build a Postgres connection string from discrete DB_* settings.

    Expected variables:
      DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    Optional:
      DB_SSLMODE
    """
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    sslmode = os.getenv("DB_SSLMODE")

    if not all([host, port, name, user, password]):
        return None

    # psycopg accepts both postgresql:// and postgres://
    url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    if sslmode:
        url = f"{url}?sslmode={sslmode}"
    return url


DATABASE_URL = os.getenv("DATABASE_URL") or _build_database_url_from_parts()
DB_ENABLED = bool(DATABASE_URL)

# -------------------------------------------------------------------
# Connection helper
# -------------------------------------------------------------------
async def get_connection():
    url = DATABASE_URL
    if not url:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL in .env (recommended) "
            "or set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."
        )

    return await psycopg.AsyncConnection.connect(url, row_factory=dict_row)

# -------------------------------------------------------------------
# Schema initialization (3-table schema: games, moves, evals)
# -------------------------------------------------------------------
async def init_db():
    """Create the minimal schema used by the app.

    NOTE: This matches the current Postgres schema:
      - games(id, raw_pgn, white, black, result, event, site, date)
      - moves(id, game_id, ply, san, fen, comment, cp_tag, color generated)
      - evals(fen pk, best_move, score_cp, score_mate, depth, pv, created_at)

    We use CREATE TABLE IF NOT EXISTS so it won't overwrite existing tables.
    """
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
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
        await conn.commit()


# -------------------------------------------------------------------
# Games + moves helpers
# -------------------------------------------------------------------
async def create_game(raw_pgn: str, headers: dict[str, str]) -> int:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO public.games (raw_pgn, white, black, result, event, site, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    raw_pgn,
                    headers.get("white"),
                    headers.get("black"),
                    headers.get("result"),
                    headers.get("event"),
                    headers.get("site"),
                    headers.get("date"),
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row["id"]


async def insert_moves(game_id: int, moves: list[dict[str, Any]]) -> None:
    """Bulk replace moves for a game.

    We choose a delete+insert strategy to work against an existing schema where
    (game_id, ply) might not currently have a UNIQUE constraint.
    """
    if not moves:
        return

    records = [
        (
            game_id,
            m["ply"],
            m["san"],
            m["fen"],
            m.get("comment"),
            bool(m.get("cp_tag", False)),
        )
        for m in moves
    ]

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            # Replace all moves for this game in a single transaction.
            await cur.execute("DELETE FROM public.moves WHERE game_id = %s", (game_id,))
            await cur.executemany(
                """
                INSERT INTO public.moves (game_id, ply, san, fen, comment, cp_tag)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                records,
            )
        await conn.commit()


async def get_moves(game_id: int) -> list[dict]:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT ply, san, fen, comment, cp_tag, color
                FROM public.moves
                WHERE game_id = %s
                ORDER BY ply ASC
                """,
                (game_id,),
            )
            rows = await cur.fetchall()
    return rows or []


# -------------------------------------------------------------------
# Evals helpers
# -------------------------------------------------------------------
async def upsert_eval(
    fen: str,
    best_move: str | None = None,
    score_cp: int | None = None,
    score_mate: int | None = None,
    depth: int | None = None,
    pv: str | None = None,
) -> None:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO public.evals (fen, best_move, score_cp, score_mate, depth, pv)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fen) DO UPDATE SET
                    best_move = EXCLUDED.best_move,
                    score_cp = EXCLUDED.score_cp,
                    score_mate = EXCLUDED.score_mate,
                    depth = EXCLUDED.depth,
                    pv = EXCLUDED.pv,
                    created_at = NOW()
                """,
                (fen, best_move, score_cp, score_mate, depth, pv),
            )
        await conn.commit()


async def get_eval(fen: str) -> Optional[dict]:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT fen, best_move, score_cp, score_mate, depth, pv, created_at
                FROM public.evals
                WHERE fen = %s
                """,
                (fen,),
            )
            return await cur.fetchone()


# -------------------------------------------------------------------
# Lightweight connectivity check
# -------------------------------------------------------------------
async def check_connection() -> bool:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 AS ok")
            row = await cur.fetchone()
            return bool(row and row.get("ok") == 1)


# -------------------------------------------------------------------
# Compatibility aliases for old route names (temporary)
# -------------------------------------------------------------------
async def ensure_schema_legacy():
    # Keep existing callers working; init_db() is now the canonical initializer.
    await init_db()
