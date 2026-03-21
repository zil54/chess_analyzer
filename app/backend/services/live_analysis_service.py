from __future__ import annotations
from fastapi import WebSocket

from app.backend.services.analysis_coordinator import analysis_coordinator
from app.backend.services.stockfish_parser import parse_stockfish_line


class LiveAnalysisService:
    async def handle_websocket(self, websocket: WebSocket) -> None:
        await analysis_coordinator.handle_websocket(websocket)

    async def shutdown(self) -> None:
        await analysis_coordinator.shutdown()


live_analysis_service = LiveAnalysisService()
