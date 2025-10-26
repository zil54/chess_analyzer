from fastapi import APIRouter, HTTPException, UploadFile, Form
from uuid import UUID
import chess.pgn
import io

from chess_analyzer.backend.db.db import (
    create_session,
    get_session,
    insert_critical_positions
)

from fastapi import APIRouter, Request, HTTPException, Response


router = APIRouter()

@router.post("/sessions")
async def new_session(pgn: str):
    session_id = await create_session(pgn)
    return {"id": session_id, "pgn": pgn, "status": "pending"}

@router.get("/sessions/{session_id}")
async def fetch_session(session_id: int):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/sessions/{session_id}/upload_pgn")
async def upload_pgn(session_id: int, file: UploadFile = Form(...)):
    pgn_text = await file.read()
    game = chess.pgn.read_game(io.StringIO(pgn_text.decode()))
    board = game.board()

    critical_positions = []

    for move in game.mainline_moves():
        board.push(move)
        # Replace with real CP detection logic if needed
        critical_positions.append((board.fullmove_number, board.fen()))

    await insert_critical_positions(session_id, critical_positions)

    return {"stored": len(critical_positions)}

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


