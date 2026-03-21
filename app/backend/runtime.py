from __future__ import annotations

import asyncio
import platform
import shutil
import sys
import warnings
from pathlib import Path

from app.backend.logs.logger import logger

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR.parent
PROJECT_ROOT = APP_DIR.parent
FRONTEND_DIST_DIR = APP_DIR / "frontend" / "dist"
_WINDOWS_POLICY_CONFIGURED = False


def configure_windows_event_loop_policy() -> None:
    """Use the selector event loop on Windows for compatibility with subprocess/websockets."""
    global _WINDOWS_POLICY_CONFIGURED

    if _WINDOWS_POLICY_CONFIGURED or not sys.platform.startswith("win"):
        return

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    _WINDOWS_POLICY_CONFIGURED = True


def get_stockfish_path() -> str:
    """Resolve the Stockfish executable for the current platform."""
    if platform.system() == "Darwin":
        stockfish_path = shutil.which("stockfish")
        if not stockfish_path:
            raise FileNotFoundError("Stockfish not found. Install with: brew install stockfish")
        return stockfish_path

    bundled_candidates = [
        APP_DIR / "engine" / "sf.exe",
        APP_DIR / "engine" / "stockfish",
    ]
    for candidate in bundled_candidates:
        if candidate.exists():
            return str(candidate)

    stockfish_path = shutil.which("stockfish")
    if stockfish_path:
        return stockfish_path

    searched = ", ".join(str(path) for path in bundled_candidates)
    logger.error("Stockfish binary not found. Checked: %s and PATH", searched)
    raise FileNotFoundError(f"Missing Stockfish binary. Checked {searched} and PATH.")
