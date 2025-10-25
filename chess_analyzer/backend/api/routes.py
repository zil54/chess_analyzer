# backend/api/routes.py
from fastapi import APIRouter, HTTPException
from uuid import UUID
from chess_analyzer.backend.db.repo import (create_session, get_session, get_latest_lines, get_history)

router = APIRouter()

@router.post("/sessions")
async def new_session(fen: str):
    session = await create_session(fen)
    return {"id": str(session.id), "fen": session.fen, "status": session.status}

@router.get("/sessions/{session_id}")
async def fetch_session(session_id: UUID):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": str(session.id),
        "fen": session.fen,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }

@router.get("/sessions/{session_id}/latest")
async def latest_lines(session_id: UUID):
    depth, rows = await get_latest_lines(session_id)
    if depth is None:
        return {"lines": []}
    return {
        "depth": depth,
        "lines": [
            {"multipv": r.multipv, "line": r.line, "updated_at": r.updated_at}
            for r in rows
        ]
    }

@router.get("/sessions/{session_id}/history")
async def history(session_id: UUID):
    rows = await get_history(session_id)
    return [
        {
            "depth": r.depth,
            "multipv": r.multipv,
            "line": r.line,
            "updated_at": r.updated_at
        }
        for r in rows
    ]