from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from app.backend.svg.svg import generate_board_svg
    from app.engine.engine import run_stockfish
    from app.engine.stockfish_session import StockfishSession
    from app.backend.logs.logger import logger
    from app.backend.api.routes import router
except ImportError:
    from app.backend.svg.svg import generate_board_svg
    from app.engine.engine import run_stockfish
    from app.engine.stockfish_session import StockfishSession
    from app.backend.logs.logger import logger
    from app.backend.api.routes import router

from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import platform
import shutil

app = FastAPI()
app.include_router(router)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base directory
base_dir = os.path.dirname(os.path.dirname(__file__))  # chess_analyzer/

# Absolute path to frontend/dist
frontend_path = os.path.join(base_dir, "frontend", "dist")

# Persistent Stockfish session

# Detect platform and find Stockfish
if platform.system() == "Darwin":  # macOS
    # Try to find stockfish in PATH (Homebrew)
    stockfish_path = shutil.which("stockfish")
    if not stockfish_path:
        logger.error("Stockfish not found in PATH. Install with: brew install stockfish")
        raise FileNotFoundError("Stockfish not found. Install with: brew install stockfish")
else:
    # Windows or other platforms
    stockfish_path = os.path.join(base_dir, "engine", "sf.exe")
    if not os.path.exists(stockfish_path):
        logger.error(f"Stockfish binary not found at: {stockfish_path}")
        raise FileNotFoundError(f"Missing Stockfish binary at: {stockfish_path}")

stockfish = StockfishSession(stockfish_path)
logger.info(f"Connected to Stockfish at: {stockfish_path}")

# Check database status
try:
    from app.backend.db.db import DB_ENABLED
    if DB_ENABLED:
        logger.info("Database is configured and enabled")
    else:
        logger.warning("Database is NOT configured. Session/PGN features will be unavailable. Set DATABASE_URL in .env to enable.")
except Exception as e:
    logger.warning(f"Database module could not be loaded: {e}")


@app.post("/analyze")
async def analyze(request: Request):
    data = await request.json()
    fen = data.get("fen", "")
    try:
        result = run_stockfish(fen, lines=3)
        if result is not None:
            logger.info("Analyze generated successfully")
            return result
        else:
            logger.error("Analyze generated but didn't produce result")
            return {"error": "No analysis result"}
    except Exception as e:
        logger.exception("SF Run produced an error")
        return {"error": str(e)}

@app.websocket("/ws/analyze")
async def analyze_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        fen = await websocket.receive_text()
        # Reset engine state to ensure fresh search from depth 1
        stockfish.send("stop")
        stockfish.send("ucinewgame")
        stockfish.send("uci")
        stockfish.send("isready")
        stockfish.send("setoption name UCI_AnalyseMode value true")
        stockfish.send("setoption name MultiPV value 3")
        stockfish.send(f"position fen {fen}")
        stockfish.send("go infinite")

        async for line in stream_stockfish():
            if "pv" in line:
                try:
                    await websocket.send_text(line)
                except WebSocketDisconnect:
                    logger.info("Client disconnected, stopping stream.")
                    stockfish.send("stop")
                    break
                except RuntimeError as e:
                    if "Cannot call \"send\"" in str(e):
                        logger.info("Tried to send after close, stopping stream.")
                        stockfish.send("stop")
                        break
                    raise
    except WebSocketDisconnect:
        logger.info("WebSocket closed before analysis finished.")
        stockfish.send("stop")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        stockfish.send("stop")


async def stream_stockfish():
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, stockfish.process.stdout.readline)
        if line:
            line = line.strip()
            logger.debug("Streaming line from Stockfish: %s", line)
            yield line
        await asyncio.sleep(0.1)  # throttle output slightly

# Mount frontend if it exists
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_vue_app(full_path: str = ""):
        return FileResponse(os.path.join(frontend_path, "index.html"))
    logger.info(f"Frontend mounted from: {frontend_path}")
else:
    logger.warning(f"Frontend not found at {frontend_path}. Build it with: cd frontend && npm install && npm run build")
    @app.get("/")
    async def root():
        return {"message": "Chess Analyzer API is running. Frontend not built yet."}


if __name__ == "__main__":
    uvicorn.run("app.backend.main:app", host="127.0.0.1", port=8000, reload=True)
