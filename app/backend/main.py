import sys
import os

# CRITICAL: Set Windows event loop policy BEFORE any asyncio imports or uvicorn startup
# This must happen at the very top before anything else creates an event loop
if sys.platform.startswith("win"):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager


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
import platform
import shutil

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Ensure DB schema exists if configured.
    try:
        from app.backend.db.db import DB_ENABLED, init_db
        if DB_ENABLED:
            await init_db()
            logger.info("DB schema ensured (games/moves/evals)")
        else:
            logger.warning(
                "Database is NOT configured. PGN upload will not persist to DB. Set DATABASE_URL in .env to enable"
            )
    except Exception as e:
        logger.warning(f"DB schema init failed: {e}")

    yield


app = FastAPI(lifespan=lifespan)

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


def parse_stockfish_line(fen: str, line: str) -> dict:
    """
    Parse a Stockfish analysis line and extract evaluation data.

    Example line: "info depth 20 seldepth 25 multipv 1 score cp 25 nodes 1234567 nps 5000000 pv e2e4 e7e5 g1f3"

    Returns: {fen, best_move, score_cp, score_mate, depth, pv, multipv}
    """
    import re

    result = {'fen': fen}

    try:
        # Extract depth
        depth_match = re.search(r'depth (\d+)', line)
        if depth_match:
            result['depth'] = int(depth_match.group(1))

        # Extract multipv (which analysis line: 1, 2, or 3)
        multipv_match = re.search(r'multipv (\d+)', line)
        if multipv_match:
            result['multipv'] = int(multipv_match.group(1))

        # Extract score (either cp or mate)
        cp_match = re.search(r'score cp (-?\d+)', line)
        mate_match = re.search(r'score mate (-?\d+)', line)

        if cp_match:
            result['score_cp'] = int(cp_match.group(1))
        elif mate_match:
            result['score_mate'] = int(mate_match.group(1))

        # Extract PV (principal variation)
        pv_match = re.search(r'pv\s+(.+?)(?:\s+$|$)', line)
        if pv_match:
            pv_line = pv_match.group(1).strip()
            moves = pv_line.split()
            if moves:
                result['best_move'] = moves[0]  # First move is the best move
                result['pv'] = ' '.join(moves[:10])  # Store first 10 moves

    except Exception as e:
        logger.error(f"Error parsing Stockfish line: {e}")

    return result



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

        min_depth_for_storage = 15  # Only store when depth >= 15
        lines_by_depth = {}  # Track all 3 lines per depth

        async for line in stream_stockfish(my_token):
            if not line:
                continue
            if " pv " in line:
                try:
                    # Parse evaluation from line
                    eval_data = parse_stockfish_line(fen, line)

                    # Collect lines by depth using multipv as line number (1, 2, or 3)
                    depth = eval_data.get('depth', 0)
                    multipv = eval_data.get('multipv', 1)  # Default to 1 if not found

                    if depth >= min_depth_for_storage:
                        if depth not in lines_by_depth:
                            lines_by_depth[depth] = {}

                        # Store by multipv number (will create dict like {1: {...}, 2: {...}, 3: {...}})
                        if multipv <= 3:  # Only store top 3
                            lines_by_depth[depth][multipv] = {
                                'best_move': eval_data.get('best_move'),
                                'score_cp': eval_data.get('score_cp'),
                                'score_mate': eval_data.get('score_mate'),
                                'pv': eval_data.get('pv')
                            }

                    # Store to database when depth reaches minimum threshold
                    if DB_ENABLED and eval_data.get('depth', 0) >= min_depth_for_storage:
                        try:
                            from app.backend.db.db import upsert_eval, store_analysis_lines

                            # Store best eval
                            await upsert_eval(
                                fen=eval_data.get('fen'),
                                best_move=eval_data.get('best_move'),
                                score_cp=eval_data.get('score_cp'),
                                score_mate=eval_data.get('score_mate'),
                                depth=eval_data.get('depth'),
                                pv=eval_data.get('pv')
                            )

                            # Store all 3 lines for this depth
                            depth = eval_data.get('depth', 0)
                            if depth in lines_by_depth and lines_by_depth[depth]:
                                # Convert dict to list for store_analysis_lines
                                lines_list = [lines_by_depth[depth].get(i) for i in range(1, 4) if i in lines_by_depth[depth]]
                                if lines_list:
                                    await store_analysis_lines(
                                        fen=fen,
                                        depth=depth,
                                        lines=lines_list
                                    )

                            logger.info(f"Stored eval + {len(lines_by_depth.get(depth, {}))} lines: depth={depth}")
                        except Exception as e:
                            logger.error(f"Failed to store evaluation: {e}")

                    await websocket.send_text(line)
                except WebSocketDisconnect:
                    logger.info("Client disconnected, stopping stream.")
                    try:
                        stockfish.send("stop")
                    except (OSError, ValueError):
                        pass  # Pipe already closed
                    break
                except RuntimeError as e:
                    if "Cannot call \"send\"" in str(e):
                        logger.info("Tried to send after close, stopping stream.")
                        try:
                            stockfish.send("stop")
                        except (OSError, ValueError):
                            pass  # Pipe already closed
                        break
                    raise

    except WebSocketDisconnect:
        logger.info("WebSocket closed before analysis finished.")
        try:
            stockfish.send("stop")
        except (OSError, ValueError):
            pass  # Pipe already closed
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        try:
            stockfish.send("stop")
        except (OSError, ValueError):
            pass  # Pipe already closed


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
