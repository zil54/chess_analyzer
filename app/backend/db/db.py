# -*- coding: utf-8 -*-
import importlib
import os
from typing import Optional, Any

from app.backend.config import load_project_env
from app.backend.runtime import configure_windows_event_loop_policy

# -------------------------------------------------------------------
# Optional psycopg import for database functionality
# -------------------------------------------------------------------
try:
    psycopg = importlib.import_module("psycopg")
    dict_row = importlib.import_module("psycopg.rows").dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    psycopg = None
    dict_row = None
    PSYCOPG_AVAILABLE = False

# -------------------------------------------------------------------
# Windows event loop fix
# -------------------------------------------------------------------
configure_windows_event_loop_policy()

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_project_env()


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
DB_ENABLED = bool(DATABASE_URL) and PSYCOPG_AVAILABLE

# -------------------------------------------------------------------
# Connection helper
# -------------------------------------------------------------------
async def get_connection():
    if not PSYCOPG_AVAILABLE:
        raise RuntimeError("psycopg library is not installed. Install it with: pip install psycopg[binary]")

    url = DATABASE_URL
    if not url:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL in .env (recommended) "
            "or set DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD."
        )

    return await psycopg.AsyncConnection.connect(url, row_factory=dict_row)

# -------------------------------------------------------------------
# Schema initialization (4-table schema: games, moves, evals, analysis_lines)
# -------------------------------------------------------------------
async def init_db():
    """Create the schema used by the app.

    NOTE: This matches the current Postgres schema:
      - games(id, raw_pgn, white, black, result, event, site, date, pgn_source, imported_at, updated_at)
      - moves(id, game_id, ply, san, fen, comment, cp_tag, color generated, variation_parent_id, variation_index, is_mainline, move_number, fen_before)
      - evals(fen pk, best_move, score_cp, score_mate, depth, pv, created_at, engine, is_tablebase, game_id)
      - analysis_lines(fen, depth, line_number pk, best_move, score_cp, score_mate, pv, updated_at)

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
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS public.quiz_results (
                    id SERIAL PRIMARY KEY,
                    game_id INT NOT NULL REFERENCES public.games(id),
                    quiz_data JSONB NOT NULL,
                    score_percentage INT,
                    total_questions INT,
                    full_answers INT,
                    partial_answers INT,
                    fail_answers INT,
                    skipped_answers INT,
                    total_credit FLOAT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(game_id)
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
                INSERT INTO public.games (raw_pgn, white, black, result, event, site, date, pgn_source, imported_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
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
                    headers.get("pgn_source"),
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
            m.get("variation_parent_id"),
            m.get("variation_index"),
            m.get("is_mainline"),
            m.get("move_number"),
            m.get("fen_before"),
        )
        for m in moves
    ]

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            # Replace all moves for this game in a single transaction.
            await cur.execute("DELETE FROM public.moves WHERE game_id = %s", (game_id,))
            await cur.executemany(
                """
                INSERT INTO public.moves (game_id, ply, san, fen, comment, cp_tag, variation_parent_id, variation_index, is_mainline, move_number, fen_before)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                records,
            )
        await conn.commit()


async def get_moves(game_id: int) -> list[dict]:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT ply, san, fen, comment, cp_tag, color, variation_parent_id, variation_index, is_mainline, move_number, fen_before
                FROM public.moves
                WHERE game_id = %s
                ORDER BY ply ASC
                """,
                (game_id,),
            )
            rows = await cur.fetchall()
    return rows or []


async def update_move_annotations(game_id: int, annotations: list[dict[str, Any]]) -> int:
    """Persist mainline move comments / critical-position tags for a game."""
    if not annotations:
        return 0

    records = [
        (
            item.get("comment"),
            bool(item.get("cp_tag", False)),
            game_id,
            item["ply"],
        )
        for item in annotations
        if item and item.get("ply") is not None
    ]

    if not records:
        return 0

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                UPDATE public.moves
                SET comment = %s,
                    cp_tag = %s
                WHERE game_id = %s AND ply = %s
                """,
                records,
            )
        await conn.commit()

    return len(records)


async def get_game_raw_pgn(game_id: int) -> Optional[str]:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT raw_pgn
                FROM public.games
                WHERE id = %s
                """,
                (game_id,),
            )
            row = await cur.fetchone()
    return row["raw_pgn"] if row else None


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
    engine: str | None = None,
    is_tablebase: bool | None = None,
    game_id: int | None = None,
) -> None:
    """
    Insert or update evaluation for a FEN position.

    Only updates if:
    - FEN not in table (new), OR
    - New depth >= existing depth (deeper or equal analysis)

    Never overwrites with shallower analysis.
    """
    import logging
    logger = logging.getLogger("chess-analyzer")

    try:
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                logger.info(f"Upserting eval: fen={fen[:40]}... best_move={best_move} score_cp={score_cp} depth={depth}")

                # Check if FEN already exists and compare depths
                await cur.execute(
                    "SELECT depth FROM public.evals WHERE fen = %s;",
                    (fen,)
                )
                existing = await cur.fetchone()

                if existing:
                    existing_depth = existing['depth'] if existing else None

                    if existing_depth and depth and depth < existing_depth:
                        logger.info(f"Skipping update: new depth {depth} < existing depth {existing_depth}")
                        return

                    logger.info(f"Updating eval: new depth {depth} >= existing {existing_depth}")

                # Insert or update
                await cur.execute(
                    """
                    INSERT INTO public.evals (fen, best_move, score_cp, score_mate, depth, pv, engine, is_tablebase, game_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (fen) DO UPDATE SET
                        best_move = EXCLUDED.best_move,
                        score_cp = EXCLUDED.score_cp,
                        score_mate = EXCLUDED.score_mate,
                        depth = EXCLUDED.depth,
                        pv = EXCLUDED.pv,
                        engine = EXCLUDED.engine,
                        is_tablebase = EXCLUDED.is_tablebase,
                        game_id = EXCLUDED.game_id,
                        created_at = NOW()
                    """,
                    (fen, best_move, score_cp, score_mate, depth, pv, engine, is_tablebase, game_id),
                )
                logger.info("[OK] Upsert query executed")
            await conn.commit()
            logger.info("[OK] Changes committed to DB")
    except Exception as e:
        logger.error("[ERROR] Error upserting eval: {0}".format(e), exc_info=True)
        raise


async def store_analysis_lines(
    fen: str,
    depth: int,
    lines: list[dict]
) -> None:
    """
    Store multiple analysis lines (e.g., top 3 variations) for a position at a specific depth.

    Args:
        fen: FEN position
        depth: Analysis depth
        lines: List of dicts with {best_move, score_cp, score_mate, pv}
    """
    import logging
    logger = logging.getLogger("chess-analyzer")

    try:
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                for line_num, line_data in enumerate(lines[:3], 1):
                    await cur.execute(
                        """
                        INSERT INTO public.analysis_lines (fen, depth, line_number, best_move, score_cp, score_mate, pv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (fen, depth, line_number) DO UPDATE SET
                            best_move = EXCLUDED.best_move,
                            score_cp = EXCLUDED.score_cp,
                            score_mate = EXCLUDED.score_mate,
                            pv = EXCLUDED.pv,
                            updated_at = NOW()
                        """,
                        (
                            fen,
                            depth,
                            line_num,
                            line_data.get('best_move'),
                            line_data.get('score_cp'),
                            line_data.get('score_mate'),
                            line_data.get('pv')
                        ),
                    )

                logger.info(f"Stored {len(lines[:3])} analysis lines at depth {depth}")

            await conn.commit()
            logger.info(f"Analysis lines committed to DB")
    except Exception as e:
        logger.error(f"Error storing analysis lines: {e}", exc_info=True)
        raise


async def get_analysis_lines(fen: str, depth: int | None = None) -> list[dict]:
    """
    Get analysis lines for a position.

    Args:
        fen: FEN position
        depth: Optional - if specified, get lines at this depth only

    Returns:
        List of analysis lines sorted by line_number
    """
    try:
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                if depth:
                    await cur.execute(
                        """
                        SELECT fen, depth, line_number, best_move, score_cp, score_mate, pv, updated_at
                        FROM public.analysis_lines
                        WHERE fen = %s AND depth = %s
                        ORDER BY line_number ASC
                        """,
                        (fen, depth),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT fen, depth, line_number, best_move, score_cp, score_mate, pv, updated_at
                        FROM public.analysis_lines
                        WHERE fen = %s
                        ORDER BY depth DESC, line_number ASC
                        """,
                        (fen,),
                    )
                rows = await cur.fetchall()
        return rows or []
    except Exception as e:
        import logging
        logger = logging.getLogger("chess-analyzer")
        logger.error(f"Error getting analysis lines: {e}")
        return []


async def get_latest_analysis_snapshot(
    fen: str,
    target_depth: int | None = None,
    prefer_richer_lines: bool = False,
) -> Optional[dict]:
    """Return the best available stored snapshot for a FEN.

    Preference order:
    1. Stored `analysis_lines` snapshot (deepest by default, or richest/deepest when `prefer_richer_lines=True`)
    2. Fallback to the top line from `evals`
    """
    eval_row = await get_eval(fen)

    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            if prefer_richer_lines:
                if target_depth is not None:
                    await cur.execute(
                        """
                        SELECT depth, COUNT(*) AS line_count
                        FROM public.analysis_lines
                        WHERE fen = %s AND depth <= %s
                        GROUP BY depth
                        ORDER BY line_count DESC, depth DESC
                        LIMIT 1
                        """,
                        (fen, target_depth),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT depth, COUNT(*) AS line_count
                        FROM public.analysis_lines
                        WHERE fen = %s
                        GROUP BY depth
                        ORDER BY line_count DESC, depth DESC
                        LIMIT 1
                        """,
                        (fen,),
                    )
            elif target_depth is not None:
                await cur.execute(
                    """
                    SELECT MAX(depth) AS depth
                    FROM public.analysis_lines
                    WHERE fen = %s AND depth <= %s
                    """,
                    (fen, target_depth),
                )
            else:
                await cur.execute(
                    """
                    SELECT MAX(depth) AS depth
                    FROM public.analysis_lines
                    WHERE fen = %s
                    """,
                    (fen,),
                )
            depth_row = await cur.fetchone()
            lines_depth = depth_row.get("depth") if depth_row else None

            if lines_depth is not None:
                await cur.execute(
                    """
                    SELECT depth, line_number, best_move, score_cp, score_mate, pv
                    FROM public.analysis_lines
                    WHERE fen = %s AND depth = %s
                    ORDER BY line_number ASC
                    """,
                    (fen, lines_depth),
                )
                lines = await cur.fetchall()
            else:
                lines = []

    if lines:
        best_line = lines[0]
        return {
            "fen": fen,
            "depth": lines_depth,
            "best_move": best_line.get("best_move"),
            "score_cp": best_line.get("score_cp"),
            "score_mate": best_line.get("score_mate"),
            "pv": best_line.get("pv"),
            "lines": list(lines),
            "created_at": eval_row.get("created_at") if eval_row else None,
        }

    if not eval_row:
        return None

    return {
        "fen": fen,
        "depth": eval_row.get("depth"),
        "best_move": eval_row.get("best_move"),
        "score_cp": eval_row.get("score_cp"),
        "score_mate": eval_row.get("score_mate"),
        "pv": eval_row.get("pv"),
        "lines": [
            {
                "depth": eval_row.get("depth"),
                "line_number": 1,
                "best_move": eval_row.get("best_move"),
                "score_cp": eval_row.get("score_cp"),
                "score_mate": eval_row.get("score_mate"),
                "pv": eval_row.get("pv"),
            }
        ],
        "created_at": eval_row.get("created_at"),
    }


async def get_eval(fen: str) -> Optional[dict]:
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT fen, best_move, score_cp, score_mate, depth, pv, created_at, engine, is_tablebase, game_id
                FROM public.evals
                WHERE fen = %s
                """,
                (fen,),
            )
            return await cur.fetchone()


# -------------------------------------------------------------------
# Quiz results helpers
# -------------------------------------------------------------------
async def save_quiz_results(game_id: int, quiz_results: dict[str, Any]) -> dict:
    """Save or update quiz results for a game."""
    import json
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO public.quiz_results (
                    game_id, quiz_data, score_percentage, total_questions,
                    full_answers, partial_answers, fail_answers, skipped_answers, total_credit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_id) DO UPDATE SET
                    quiz_data = EXCLUDED.quiz_data,
                    score_percentage = EXCLUDED.score_percentage,
                    total_questions = EXCLUDED.total_questions,
                    full_answers = EXCLUDED.full_answers,
                    partial_answers = EXCLUDED.partial_answers,
                    fail_answers = EXCLUDED.fail_answers,
                    skipped_answers = EXCLUDED.skipped_answers,
                    total_credit = EXCLUDED.total_credit,
                    updated_at = NOW()
                RETURNING id, created_at, updated_at
                """,
                (
                    game_id,
                    json.dumps(quiz_results.get("entries", [])),
                    quiz_results.get("score_percentage"),
                    quiz_results.get("total_questions"),
                    quiz_results.get("full_answers"),
                    quiz_results.get("partial_answers"),
                    quiz_results.get("fail_answers"),
                    quiz_results.get("skipped_answers"),
                    quiz_results.get("total_credit"),
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
    return row or {}


async def get_quiz_results(game_id: int) -> Optional[dict]:
    """Retrieve saved quiz results for a game."""
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, game_id, quiz_data, score_percentage, total_questions,
                       full_answers, partial_answers, fail_answers, skipped_answers,
                       total_credit, created_at, updated_at
                FROM public.quiz_results
                WHERE game_id = %s
                """,
                (game_id,),
            )
            row = await cur.fetchone()

    if not row:
        return None

    import json
    try:
        entries = json.loads(row.get("quiz_data", "[]"))
    except:
        entries = []

    return {
        "id": row.get("id"),
        "game_id": row.get("game_id"),
        "score_percentage": row.get("score_percentage"),
        "total_questions": row.get("total_questions"),
        "full_answers": row.get("full_answers"),
        "partial_answers": row.get("partial_answers"),
        "fail_answers": row.get("fail_answers"),
        "skipped_answers": row.get("skipped_answers"),
        "total_credit": row.get("total_credit"),
        "entries": entries,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


async def delete_quiz_results(game_id: int) -> int:
    """Delete quiz results for a game."""
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM public.quiz_results WHERE game_id = %s",
                (game_id,),
            )
            rows_deleted = cur.rowcount
        await conn.commit()
    return rows_deleted


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
