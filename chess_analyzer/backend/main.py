from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.svg.svg import generate_board_svg
from engine.engine import run_stockfish
from engine.stockfish_session import StockfishSession
import uvicorn
import asyncio
import os
import platform
import shutil
from backend.logs.logger import logger
from backend.api.routes import router as api_router
from fastapi.staticfiles import StaticFiles
app = FastAPI()
app.include_router(api_router)

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
    from backend.db.db import DB_ENABLED
    if DB_ENABLED:
        logger.info("Database is configured and enabled")
    else:
        logger.warning("Database is NOT configured. Session/PGN features will be unavailable. Set DATABASE_URL in .env to enable.")
except Exception as e:
    logger.warning(f"Database module could not be loaded: {e}")


@app.post("/svg")
async def svg(request: Request):
    data = await request.json()
    fen = data.get("fen", "")
    logger.info("Received FEN for SVG: %s", fen)

    try:
        svg_markup = generate_board_svg(fen)
        if not svg_markup or "<svg" not in svg_markup:
            logger.error("SVG generation failed or malformed")
            return Response(content="SVG generation failed", status_code=500)

        logger.info("SVG generated successfully")
        return Response(content=svg_markup, media_type="image/svg+xml")

    except Exception as e:
        logger.exception("SVG generation error")
        return Response(content="SVG generation error", status_code=500)

@app.post("/analyze")
async def analyze(request: Request):
    data = await request.json()
    fen = data.get("fen", "")
    try:
        result = run_stockfish(fen, lines=3)
        return result
        if result is not None:
            logger.info("Analyze generated successfully")
        else:
            logger.error("Analyze generated but didn't produce result")
    except Exception as e:
        return {"error": str(e)}
        logger.exception("SF Run produced an error")

@app.websocket("/ws/analyze")
async def analyze_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        fen = await websocket.receive_text()
        stockfish.send("uci")
        stockfish.send("setoption name MultiPV value 3")
        stockfish.send(f"position fen {fen}")
        stockfish.send("go infinite")

        async for line in stream_stockfish():
            if "pv" in line:
                try:
                    await websocket.send_text(line)
                except WebSocketDisconnect:
                    logger.info("Client disconnected, stopping stream.")
                    break
                except RuntimeError as e:
                    if "Cannot call \"send\"" in str(e):
                        logger.info("Tried to send after close, stopping stream.")
                        break
                    raise
    except WebSocketDisconnect:
        logger.info("WebSocket closed before analysis finished.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        # ⚠️ Don't send to client here, socket may be closed


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
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

