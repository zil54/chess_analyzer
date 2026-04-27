# -*- coding: utf-8 -*-
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.backend.api.routes import router as api_router
from app.backend.api.ws_routes import router as websocket_router
from app.backend.logs.logger import logger
from app.backend.runtime import FRONTEND_DIST_DIR
from app.backend.services.live_analysis_service import live_analysis_service
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.backend.db.db import DB_ENABLED, init_db
        if DB_ENABLED:
            await init_db()
            logger.info("DB schema ensured (games/moves/evals)")
        else:
            logger.warning(
                "Database is NOT configured. PGN upload will not persist to DB. Set DATABASE_URL in .env to enable"
            )
    except Exception as exc:
        logger.warning("DB schema init failed: %s", exc)
    try:
        yield
    finally:
        await live_analysis_service.shutdown()
def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(api_router)
    app.include_router(websocket_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _log_database_status()
    _mount_frontend(app)
    return app
def _log_database_status() -> None:
    try:
        from app.backend.db.db import DB_ENABLED
        if DB_ENABLED:
            logger.info("Database is configured and enabled")
        else:
            logger.warning(
                "Database is NOT configured. Session/PGN features will be unavailable. Set DATABASE_URL in .env to enable."
            )
    except Exception as exc:
        logger.warning("Database module could not be loaded: %s", exc)
def _mount_frontend(app: FastAPI) -> None:
    frontend_path = str(FRONTEND_DIST_DIR)
    if FRONTEND_DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
        @app.get("/")
        @app.get("/{full_path:path}")
        async def serve_vue_app(full_path: str = ""):
            return FileResponse(FRONTEND_DIST_DIR / "index.html")
        logger.info("Frontend mounted from: %s", frontend_path)
        return
    logger.warning(
        "Frontend not found at %s. Build it with: cd frontend && npm install && npm run build",
        frontend_path,
    )
    @app.get("/")
    async def root():
        return {"message": "Chess Analyzer API is running. Frontend not built yet."}
