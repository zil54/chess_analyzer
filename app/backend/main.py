from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
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

# Global token increments for each new analysis run; used to cancel older stream loops
analysis_run_token = 0
analysis_run_lock = asyncio.Lock()


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
    global analysis_run_token

    # Each websocket gets its own token; if a new analysis starts, older one stops streaming
    async with analysis_run_lock:
        analysis_run_token += 1
        my_token = analysis_run_token

    try:
        fen = await websocket.receive_text()

        # Make sure any previous infinite search is stopped and its output is flushed
        await reset_stockfish_for_new_analysis(fen)

        async for line in stream_stockfish(my_token):
            if not line:
                continue
            if " pv " in line:
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


async def reset_stockfish_for_new_analysis(fen: str):
    """Reset stockfish to a known clean state before starting a new infinite search.

    This prevents leftover buffered output from a previous search (often higher depth)
    from being read and sent to the client during a new search.
    """
    loop = asyncio.get_event_loop()

    def _do_reset():
        with stockfish.lock:
            stockfish.process.stdin.write("stop\n")
            stockfish.process.stdin.write("ucinewgame\n")
            stockfish.process.stdin.write("isready\n")
            stockfish.process.stdin.flush()

            # Drain output until readyok so we start with a clean boundary.
            while True:
                out_line = stockfish.process.stdout.readline()
                if not out_line:
                    break
                out_line = out_line.strip()
                if out_line == "readyok":
                    break

            stockfish.process.stdin.write("setoption name UCI_AnalyseMode value true\n")
            stockfish.process.stdin.write("setoption name MultiPV value 3\n")
            stockfish.process.stdin.write(f"position fen {fen}\n")
            stockfish.process.stdin.write("go infinite\n")
            stockfish.process.stdin.flush()

    future = loop.run_in_executor(None, _do_reset, *())
    await future


async def stream_stockfish(my_token: int):
    global analysis_run_token
    loop = asyncio.get_event_loop()
    while True:
        # If a newer analysis run started, stop streaming from this one.
        if my_token != analysis_run_token:
            break

        future = loop.run_in_executor(None, stockfish.process.stdout.readline)
        line = await future

        # Token could change while we were blocked on readline
        if my_token != analysis_run_token:
            break

        if line:
            line = line.strip()
            logger.debug("Streaming line from Stockfish: %s", line)
            yield line

        await asyncio.sleep(0.05)  # throttle output slightly


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
