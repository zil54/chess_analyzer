# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket
from app.backend.services.live_analysis_service import live_analysis_service
router = APIRouter()
@router.websocket("/ws/analyze")
async def analyze_ws(websocket: WebSocket) -> None:
    await live_analysis_service.handle_websocket(websocket)
