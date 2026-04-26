# -*- coding: utf-8 -*-
import sys
from pathlib import Path

SCRIPT_MODE = __package__ in {None, ""}
APP_IMPORT_PATH = "main:app" if SCRIPT_MODE else "app.backend.main:app"

if SCRIPT_MODE:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from app.backend.runtime import configure_windows_event_loop_policy

configure_windows_event_loop_policy()

from app.backend.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(APP_IMPORT_PATH, host="127.0.0.1", port=8000, reload=True)
