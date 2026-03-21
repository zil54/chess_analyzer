from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parent

DEFAULT_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH = 10
DEFAULT_LIVE_ANALYSIS_WORKER_TARGET_DEPTH = 70
DEFAULT_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH = 2
DEFAULT_LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA = 3
MAX_ANALYSIS_DEPTH = 70
MAX_DISPLAY_LAG_DEPTH = 10
MAX_CACHE_UNLOCK_DEPTH_DELTA = 10


@lru_cache(maxsize=1)
def load_project_env() -> None:
    root_dotenv = PROJECT_ROOT / ".env"
    backend_dotenv = BACKEND_DIR / ".env"

    load_dotenv(dotenv_path=root_dotenv, override=False)
    load_dotenv(dotenv_path=backend_dotenv, override=False)

    try:
        discovered = find_dotenv(usecwd=True)
        if discovered:
            load_dotenv(dotenv_path=discovered, override=False)
    except Exception:
        pass


def _get_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value in {None, ""}:
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default

    return max(minimum, min(value, maximum))


load_project_env()

LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH = _get_int_env(
    "LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH",
    DEFAULT_LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
    1,
    MAX_ANALYSIS_DEPTH,
)
LIVE_ANALYSIS_WORKER_TARGET_DEPTH = _get_int_env(
    "LIVE_ANALYSIS_WORKER_TARGET_DEPTH",
    DEFAULT_LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
    1,
    MAX_ANALYSIS_DEPTH,
)
LIVE_ANALYSIS_DISPLAY_LAG_DEPTH = _get_int_env(
    "LIVE_ANALYSIS_DISPLAY_LAG_DEPTH",
    DEFAULT_LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
    0,
    MAX_DISPLAY_LAG_DEPTH,
)
LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA = _get_int_env(
    "LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA",
    DEFAULT_LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA,
    0,
    MAX_CACHE_UNLOCK_DEPTH_DELTA,
)
