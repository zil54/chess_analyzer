from fastapi import APIRouter, HTTPException, UploadFile, Form, Request, Response
from uuid import UUID
import chess
import chess.pgn
import chess.svg
import io
import time

try:
    from backend.db.db import (
        create_session,
        get_session,
        insert_critical_positions,
        DB_ENABLED
    )
except Exception:
    DB_ENABLED = False

router = APIRouter()

@router.post("/sessions")
async def new_session(request: Request):
    try:
        data = await request.json()
        pgn = data.get("pgn", "")
    except Exception:
        # If JSON parsing fails, try form data
        form = await request.form()
        pgn = form.get("pgn", "")

    if not pgn:
        raise HTTPException(status_code=400, detail="PGN data is required")

    # Validate PGN format
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if not game:
            raise ValueError("Invalid PGN format")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PGN: {str(e)}")

    # If database is enabled, persist the session
    if DB_ENABLED:
        session_id = await create_session(pgn)
        return {"id": session_id, "pgn": pgn, "status": "pending"}
    else:
        # Without database, generate a temporary ID and return immediately
        session_id = int(time.time() * 1000)  # Use timestamp as ID
        return {"id": session_id, "pgn": pgn, "status": "ready", "note": "Session not persisted (database disabled)"}

@router.get("/sessions/{session_id}")
async def fetch_session(session_id: int):
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not configured. Set DATABASE_URL in .env file.")
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/sessions/{session_id}/upload_pgn")
async def upload_pgn(session_id: int, file: UploadFile):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    try:
        pgn_text = await file.read()
        pgn_str = pgn_text.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if not game:
            raise ValueError("No valid game found in PGN")

        board = game.board()
        critical_positions = []

        for move in game.mainline_moves():
            board.push(move)
            # Replace with real CP detection logic if needed
            critical_positions.append({
                "move_number": board.fullmove_number,
                "fen": board.fen(),
                "move": move.uci()
            })

        if not critical_positions:
            raise HTTPException(status_code=400, detail="No moves found in PGN")

        # If database is enabled, persist the positions
        if DB_ENABLED:
            await insert_critical_positions(session_id, [(p["move_number"], p["fen"]) for p in critical_positions])
            return {"stored": len(critical_positions), "positions": len(critical_positions)}
        else:
            # Without database, return positions directly
            return {
                "stored": 0,
                "positions": len(critical_positions),
                "critical_positions": critical_positions,
                "note": "Positions not persisted (database disabled)"
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid PGN format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PGN: {str(e)}")

@router.post("/analyze_pgn")
async def analyze_pgn(request: Request):
    """
    Parse a PGN and return all positions (works without database)
    Accepts either JSON with {"pgn": "..."} or multipart file upload
    """
    try:
        # Try JSON first
        data = await request.json()
        pgn_str = data.get("pgn", "")
    except Exception:
        # Try form data with file upload
        try:
            form = await request.form()
            if "file" in form:
                file = form["file"]
                pgn_text = await file.read()
                pgn_str = pgn_text.decode('utf-8')
            elif "pgn" in form:
                pgn_str = form["pgn"]
            else:
                raise HTTPException(status_code=400, detail="No PGN data provided")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PGN: {str(e)}")

    if not pgn_str:
        raise HTTPException(status_code=400, detail="PGN data is required")

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if not game:
            raise ValueError("No valid game found in PGN")

        # Extract game metadata
        headers = {
            "event": game.headers.get("Event", "Unknown"),
            "white": game.headers.get("White", "Unknown"),
            "black": game.headers.get("Black", "Unknown"),
            "date": game.headers.get("Date", "Unknown"),
            "result": game.headers.get("Result", "*")
        }

        board = game.board()
        positions = []

        # Add starting position
        positions.append({
            "move_number": 0,
            "fen": board.fen(),
            "move": None,
            "san": None
        })

        # Process all moves
        for move in game.mainline_moves():
            san = board.san(move)
            board.push(move)
            positions.append({
                "move_number": board.fullmove_number,
                "fen": board.fen(),
                "move": move.uci(),
                "san": san
            })

        return {
            "success": True,
            "headers": headers,
            "total_moves": len(positions) - 1,
            "positions": positions
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid PGN format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PGN: {str(e)}")

@router.post("/svg")
async def render_svg(request: Request):
    data = await request.json()
    fen = data.get("fen")
    if not fen:
        raise HTTPException(status_code=400, detail="Missing FEN")

    try:
        board = chess.Board(fen)
        svg = chess.svg.board(board)
        return Response(content=svg, media_type="image/svg+xml")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {str(e)}")


