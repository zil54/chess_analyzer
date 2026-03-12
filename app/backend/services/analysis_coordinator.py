from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, replace
from typing import Any

import chess
from fastapi import WebSocket, WebSocketDisconnect

from app.backend.config import (
    LIVE_ANALYSIS_DISPLAY_LAG_DEPTH,
    LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH,
    LIVE_ANALYSIS_WORKER_TARGET_DEPTH,
    MAX_ANALYSIS_DEPTH,
    MAX_DISPLAY_LAG_DEPTH,
)
from app.backend.logs.logger import logger
from app.backend.runtime import get_stockfish_path
from app.backend.services.stockfish_parser import parse_stockfish_line
from app.engine.stockfish_session import StockfishSession

DEFAULT_DISPLAY_TARGET_DEPTH = LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH
DEFAULT_WORKER_DEPTH_OFFSET = 6
DEFAULT_WORKER_TARGET_DEPTH = max(LIVE_ANALYSIS_WORKER_TARGET_DEPTH, DEFAULT_DISPLAY_TARGET_DEPTH)
DEFAULT_DISPLAY_LAG_DEPTH = LIVE_ANALYSIS_DISPLAY_LAG_DEPTH
DEFAULT_MULTIPV = 3


@dataclass(frozen=True)
class AnalysisRequest:
    fen: str
    display_target_depth: int
    worker_target_depth: int
    display_lag_depth: int


@dataclass
class AnalysisJob:
    fen: str
    worker_target_depth: int
    multipv: int
    task: asyncio.Task[None]


class AnalysisCoordinator:
    def __init__(self, poll_interval: float = 0.35) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._jobs_lock = asyncio.Lock()
        self._poll_interval = poll_interval

    async def handle_websocket(self, websocket: WebSocket) -> None:
        await websocket.accept()

        try:
            request_payload = await websocket.receive_text()
            request = self.parse_request_payload(request_payload)
            chess.Board(request.fen)

            if not self._db_enabled():
                await self._stream_direct_engine(websocket, request)
                return

            latest_snapshot = await self.get_snapshot(request.fen)
            latest_depth = self._snapshot_depth(latest_snapshot)
            display_snapshot = latest_snapshot
            if latest_snapshot and self._snapshot_line_count(latest_snapshot) < DEFAULT_MULTIPV:
                display_snapshot = await self.get_snapshot(
                    request.fen,
                    latest_depth,
                    prefer_richer_lines=True,
                ) or latest_snapshot
            request = self._with_effective_worker_target(request, latest_depth)
            if latest_snapshot and latest_depth >= MAX_ANALYSIS_DEPTH:
                await websocket.send_json(
                    self.build_snapshot_event(
                        display_snapshot,
                        request,
                        source="database",
                        worker_depth=latest_depth,
                        worker_running=False,
                    )
                )
                await websocket.send_json(
                    self.build_status_event(
                        request,
                        "complete",
                        "database cache hit at max depth",
                        display_depth=latest_depth,
                        worker_depth=latest_depth,
                        worker_running=False,
                    )
                )
                return

            started = await self.ensure_analysis(request.fen, request.worker_target_depth)
            latest_depth = self._snapshot_depth(latest_snapshot)
            if latest_snapshot:
                await websocket.send_json(
                    self.build_snapshot_event(
                        display_snapshot,
                        request,
                        source="database",
                        worker_depth=latest_depth,
                        worker_running=True,
                    )
                )

            status = "analysis_started" if started else "analysis_running"
            status_message = None
            if latest_snapshot and latest_depth >= request.display_target_depth:
                status_message = f"Serving cached depth {latest_depth} while worker deepens to {request.worker_target_depth}"

            await websocket.send_json(
                self.build_status_event(
                    request,
                    status,
                    status_message,
                    display_depth=latest_depth if latest_snapshot else None,
                    worker_depth=latest_depth if latest_snapshot else None,
                    worker_running=True,
                )
            )
            await self._stream_database_updates(websocket, request, latest_snapshot)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during analysis stream")
        except ValueError as exc:
            await self._send_error(websocket, str(exc))
        except Exception as exc:  # pragma: no cover - defensive integration path
            logger.error("Unexpected websocket analysis error: %s", exc, exc_info=True)
            await self._send_error(websocket, f"Analysis failed: {exc}")

    async def shutdown(self) -> None:
        async with self._jobs_lock:
            jobs = list(self._jobs.values())
            self._jobs.clear()

        for job in jobs:
            job.task.cancel()

        if jobs:
            await asyncio.gather(*(job.task for job in jobs), return_exceptions=True)

    @staticmethod
    def parse_request_payload(payload: str) -> AnalysisRequest:
        fen = payload.strip()
        display_target_depth = DEFAULT_DISPLAY_TARGET_DEPTH
        worker_target_depth = DEFAULT_WORKER_TARGET_DEPTH
        display_lag_depth = DEFAULT_DISPLAY_LAG_DEPTH

        if not fen:
            raise ValueError("FEN is required")

        if fen.startswith("{"):
            data = json.loads(fen)
            fen = str(data.get("fen", "")).strip()
            display_target_depth = AnalysisCoordinator._clamp_depth(
                data.get("display_target_depth", data.get("depth", DEFAULT_DISPLAY_TARGET_DEPTH)),
                DEFAULT_DISPLAY_TARGET_DEPTH,
            )
            worker_target_depth = AnalysisCoordinator._clamp_depth(
                data.get("worker_target_depth", data.get("worker_depth", display_target_depth + DEFAULT_WORKER_DEPTH_OFFSET)),
                max(DEFAULT_WORKER_TARGET_DEPTH, display_target_depth + DEFAULT_WORKER_DEPTH_OFFSET),
            )
            display_lag_depth = AnalysisCoordinator._clamp_lag(
                data.get("display_lag_depth", data.get("lag_depth", DEFAULT_DISPLAY_LAG_DEPTH))
            )
        else:
            display_target_depth = AnalysisCoordinator._clamp_depth(display_target_depth, DEFAULT_DISPLAY_TARGET_DEPTH)
            worker_target_depth = AnalysisCoordinator._clamp_depth(
                max(DEFAULT_WORKER_TARGET_DEPTH, display_target_depth + DEFAULT_WORKER_DEPTH_OFFSET),
                DEFAULT_WORKER_TARGET_DEPTH,
            )

        if not fen:
            raise ValueError("FEN is required")

        worker_target_depth = max(display_target_depth, worker_target_depth)
        return AnalysisRequest(
            fen=fen,
            display_target_depth=display_target_depth,
            worker_target_depth=worker_target_depth,
            display_lag_depth=display_lag_depth,
        )

    @staticmethod
    def _with_effective_worker_target(request: AnalysisRequest, cached_depth: int) -> AnalysisRequest:
        if cached_depth < request.worker_target_depth or cached_depth >= MAX_ANALYSIS_DEPTH:
            return request

        extended_target = min(MAX_ANALYSIS_DEPTH, cached_depth + DEFAULT_WORKER_DEPTH_OFFSET)
        if extended_target <= request.worker_target_depth:
            return request

        return replace(request, worker_target_depth=extended_target)

    @staticmethod
    def _clamp_depth(value: Any, default: int) -> int:
        try:
            return max(1, min(int(value or default), MAX_ANALYSIS_DEPTH))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp_lag(value: Any) -> int:
        try:
            return max(0, min(int(value or 0), MAX_DISPLAY_LAG_DEPTH))
        except (TypeError, ValueError):
            return DEFAULT_DISPLAY_LAG_DEPTH

    @staticmethod
    def build_status_event(
        request: AnalysisRequest,
        status: str,
        message: str | None = None,
        *,
        display_depth: int | None = None,
        worker_depth: int | None = None,
        worker_running: bool | None = None,
    ) -> dict[str, Any]:
        event = {
            "type": "status",
            "fen": request.fen,
            "target_depth": request.display_target_depth,
            "display_target_depth": request.display_target_depth,
            "worker_target_depth": request.worker_target_depth,
            "display_lag_depth": request.display_lag_depth,
            "status": status,
        }
        if message:
            event["message"] = message
        if display_depth is not None:
            event["display_depth"] = int(display_depth)
            event["display_complete"] = int(display_depth) >= request.display_target_depth
        if worker_depth is not None:
            event["worker_depth"] = int(worker_depth)
        if worker_running is not None:
            event["worker_running"] = worker_running
            if worker_depth is not None:
                event["worker_complete"] = int(worker_depth) >= request.worker_target_depth and not worker_running
        return event

    @staticmethod
    def build_snapshot_event(
        snapshot: dict[str, Any],
        request: AnalysisRequest,
        source: str,
        *,
        worker_depth: int | None = None,
        worker_running: bool = False,
    ) -> dict[str, Any]:
        depth = AnalysisCoordinator._snapshot_depth(snapshot)
        latest_worker_depth = max(depth, int(worker_depth or 0))
        display_complete = depth >= request.display_target_depth
        return {
            "type": "snapshot",
            "fen": snapshot.get("fen"),
            "depth": depth,
            "target_depth": request.display_target_depth,
            "display_target_depth": request.display_target_depth,
            "worker_target_depth": request.worker_target_depth,
            "display_lag_depth": request.display_lag_depth,
            "complete": display_complete,
            "display_complete": display_complete,
            "worker_depth": latest_worker_depth,
            "worker_running": worker_running,
            "worker_complete": latest_worker_depth >= request.worker_target_depth and not worker_running,
            "source": source,
            "best_move": snapshot.get("best_move"),
            "score_cp": snapshot.get("score_cp"),
            "score_mate": snapshot.get("score_mate"),
            "pv": snapshot.get("pv"),
            "lines": snapshot.get("lines", []),
        }

    async def get_snapshot(
        self,
        fen: str,
        target_depth: int | None = None,
        prefer_richer_lines: bool = False,
    ) -> dict[str, Any] | None:
        from app.backend.db.db import get_latest_analysis_snapshot

        return await get_latest_analysis_snapshot(fen, target_depth, prefer_richer_lines=prefer_richer_lines)

    async def ensure_analysis(self, fen: str, worker_target_depth: int, multipv: int = DEFAULT_MULTIPV) -> bool:
        async with self._jobs_lock:
            existing = self._jobs.get(fen)
            if existing and not existing.task.done():
                existing.worker_target_depth = max(existing.worker_target_depth, worker_target_depth)
                return False

            task = asyncio.create_task(self._run_analysis_job(fen))
            self._jobs[fen] = AnalysisJob(
                fen=fen,
                worker_target_depth=worker_target_depth,
                multipv=multipv,
                task=task,
            )
            return True

    async def _stream_database_updates(
        self,
        websocket: WebSocket,
        request: AnalysisRequest,
        initial_snapshot: dict[str, Any] | None,
    ) -> None:
        last_sent_signature = self._snapshot_signature(initial_snapshot)
        last_sent_depth = self._snapshot_depth(initial_snapshot)

        while True:
            latest_snapshot = await self.get_snapshot(request.fen)
            worker_running = await self._job_is_running(request.fen)
            display_snapshot = await self._resolve_display_snapshot(request, latest_snapshot, worker_running)
            display_signature = self._snapshot_signature(display_snapshot)
            display_depth = self._snapshot_depth(display_snapshot)
            latest_depth = self._snapshot_depth(latest_snapshot)

            should_send_display = bool(
                display_snapshot and (
                    display_depth > last_sent_depth or
                    (display_depth == last_sent_depth and display_signature != last_sent_signature)
                )
            )
            if should_send_display:
                await websocket.send_json(
                    self.build_snapshot_event(
                        display_snapshot,
                        request,
                        source="database",
                        worker_depth=latest_depth,
                        worker_running=worker_running,
                    )
                )
                last_sent_signature = display_signature
                last_sent_depth = display_depth

            if not worker_running:
                if latest_snapshot:
                    latest_signature = self._snapshot_signature(latest_snapshot)
                    if latest_signature != last_sent_signature:
                        await websocket.send_json(
                            self.build_snapshot_event(
                                latest_snapshot,
                                request,
                                source="database",
                                worker_depth=latest_depth,
                                worker_running=False,
                            )
                        )
                        last_sent_signature = latest_signature
                        last_sent_depth = latest_depth

                    await websocket.send_json(
                        self.build_status_event(
                            request,
                            "complete",
                            display_depth=last_sent_depth,
                            worker_depth=latest_depth,
                            worker_running=False,
                        )
                    )
                else:
                    await websocket.send_json(
                        self.build_status_event(
                            request,
                            "idle",
                            "No analysis snapshot available",
                            worker_depth=0,
                            worker_running=False,
                        )
                    )
                return

            await asyncio.sleep(self._poll_interval)

    async def _run_analysis_job(self, fen: str) -> None:
        session = StockfishSession(get_stockfish_path())
        lines_by_depth: dict[int, dict[int, dict[str, Any]]] = {}
        last_persisted_signature: tuple[int, tuple[int, ...]] | None = None

        try:
            session.send("uci")
            session.send("ucinewgame")
            session.send("setoption name UCI_AnalyseMode value true")
            session.send(f"setoption name MultiPV value {DEFAULT_MULTIPV}")
            session.send(f"position fen {fen}")
            session.send("go infinite")

            while True:
                line = await asyncio.to_thread(session.process.stdout.readline)
                if not line:
                    break

                parsed = parse_stockfish_line(fen, line.strip())
                if not parsed or "pv" not in parsed:
                    continue

                depth = int(parsed.get("depth", 0) or 0)
                multipv = int(parsed.get("multipv", 1) or 1)
                if depth < 1 or multipv < 1 or multipv > DEFAULT_MULTIPV:
                    continue

                depth_bucket = lines_by_depth.setdefault(depth, {})
                depth_bucket[multipv] = {
                    "best_move": parsed.get("best_move"),
                    "score_cp": parsed.get("score_cp"),
                    "score_mate": parsed.get("score_mate"),
                    "pv": parsed.get("pv"),
                }

                signature = (depth, tuple(sorted(depth_bucket)))
                if signature != last_persisted_signature:
                    await self._persist_depth_snapshot(fen, depth, depth_bucket)
                    last_persisted_signature = signature

                worker_target_depth = await self._get_job_worker_target_depth(fen)
                if depth >= worker_target_depth and 1 in depth_bucket:
                    return
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - integration path
            logger.error("Background analysis job failed for fen %s: %s", fen, exc, exc_info=True)
        finally:
            try:
                session.send("stop")
                session.send("quit")
            except Exception:
                pass
            try:
                if session.process.poll() is None:
                    session.process.terminate()
                    await asyncio.to_thread(session.process.wait, 2)
            except Exception:
                try:
                    session.process.kill()
                except Exception:
                    pass
            async with self._jobs_lock:
                job = self._jobs.get(fen)
                if job and job.task is asyncio.current_task():
                    self._jobs.pop(fen, None)

    async def _persist_depth_snapshot(self, fen: str, depth: int, depth_bucket: dict[int, dict[str, Any]]) -> None:
        from app.backend.db.db import store_analysis_lines, upsert_eval

        ordered_lines = [depth_bucket[idx] for idx in range(1, DEFAULT_MULTIPV + 1) if idx in depth_bucket]
        if not ordered_lines:
            return

        best_line = ordered_lines[0]
        await upsert_eval(
            fen=fen,
            best_move=best_line.get("best_move"),
            score_cp=best_line.get("score_cp"),
            score_mate=best_line.get("score_mate"),
            depth=depth,
            pv=best_line.get("pv"),
        )
        await store_analysis_lines(fen=fen, depth=depth, lines=ordered_lines)

    async def _stream_direct_engine(self, websocket: WebSocket, request: AnalysisRequest) -> None:
        session = StockfishSession(get_stockfish_path())
        lines_by_depth: dict[int, dict[int, dict[str, Any]]] = {}
        last_sent_signature: tuple[int, tuple[tuple[int, str | None], ...]] | None = None
        last_sent_depth = 0

        try:
            session.send("uci")
            session.send("ucinewgame")
            session.send("setoption name UCI_AnalyseMode value true")
            session.send(f"setoption name MultiPV value {DEFAULT_MULTIPV}")
            session.send(f"position fen {request.fen}")
            session.send("go infinite")
            await websocket.send_json(
                self.build_status_event(
                    request,
                    "analysis_started",
                    "Database disabled; streaming engine directly",
                    worker_running=True,
                )
            )

            while True:
                line = await asyncio.to_thread(session.process.stdout.readline)
                if not line:
                    break

                parsed = parse_stockfish_line(request.fen, line.strip())
                if not parsed or "pv" not in parsed:
                    continue

                depth = int(parsed.get("depth", 0) or 0)
                multipv = int(parsed.get("multipv", 1) or 1)
                if depth < 1 or multipv < 1 or multipv > DEFAULT_MULTIPV:
                    continue

                depth_bucket = lines_by_depth.setdefault(depth, {})
                depth_bucket[multipv] = {
                    "line_number": multipv,
                    "best_move": parsed.get("best_move"),
                    "score_cp": parsed.get("score_cp"),
                    "score_mate": parsed.get("score_mate"),
                    "pv": parsed.get("pv"),
                }

                display_depth = depth if depth <= request.display_lag_depth else max(
                    candidate_depth
                    for candidate_depth in lines_by_depth
                    if candidate_depth <= depth - request.display_lag_depth
                )
                display_bucket = lines_by_depth[display_depth]
                snapshot = {
                    "fen": request.fen,
                    "depth": display_depth,
                    "best_move": display_bucket[min(display_bucket)].get("best_move"),
                    "score_cp": display_bucket[min(display_bucket)].get("score_cp"),
                    "score_mate": display_bucket[min(display_bucket)].get("score_mate"),
                    "pv": display_bucket[min(display_bucket)].get("pv"),
                    "lines": [display_bucket[idx] for idx in range(1, DEFAULT_MULTIPV + 1) if idx in display_bucket],
                }
                signature = self._snapshot_signature(snapshot)
                snapshot_depth = self._snapshot_depth(snapshot)
                if signature != last_sent_signature and snapshot_depth >= last_sent_depth:
                    await websocket.send_json(
                        self.build_snapshot_event(
                            snapshot,
                            request,
                            source="engine",
                            worker_depth=depth,
                            worker_running=True,
                        )
                    )
                    last_sent_signature = signature
                    last_sent_depth = snapshot_depth

                if depth >= request.worker_target_depth and 1 in depth_bucket:
                    final_bucket = lines_by_depth[depth]
                    final_snapshot = {
                        "fen": request.fen,
                        "depth": depth,
                        "best_move": final_bucket[min(final_bucket)].get("best_move"),
                        "score_cp": final_bucket[min(final_bucket)].get("score_cp"),
                        "score_mate": final_bucket[min(final_bucket)].get("score_mate"),
                        "pv": final_bucket[min(final_bucket)].get("pv"),
                        "lines": [final_bucket[idx] for idx in range(1, DEFAULT_MULTIPV + 1) if idx in final_bucket],
                    }
                    final_signature = self._snapshot_signature(final_snapshot)
                    if final_signature != last_sent_signature:
                        await websocket.send_json(
                            self.build_snapshot_event(
                                final_snapshot,
                                request,
                                source="engine",
                                worker_depth=depth,
                                worker_running=False,
                            )
                        )
                    await websocket.send_json(
                        self.build_status_event(
                            request,
                            "complete",
                            display_depth=depth,
                            worker_depth=depth,
                            worker_running=False,
                        )
                    )
                    return
        finally:
            try:
                session.send("stop")
                session.send("quit")
            except Exception:
                pass
            try:
                if session.process.poll() is None:
                    session.process.terminate()
                    await asyncio.to_thread(session.process.wait, 2)
            except Exception:
                try:
                    session.process.kill()
                except Exception:
                    pass

    async def _resolve_display_snapshot(
        self,
        request: AnalysisRequest,
        latest_snapshot: dict[str, Any] | None,
        worker_running: bool,
    ) -> dict[str, Any] | None:
        if not latest_snapshot:
            return None

        if not worker_running or request.display_lag_depth <= 0:
            return latest_snapshot

        latest_depth = self._snapshot_depth(latest_snapshot)
        display_cap = latest_depth - request.display_lag_depth
        if display_cap < 1:
            return latest_snapshot

        capped_snapshot = await self.get_snapshot(request.fen, display_cap, prefer_richer_lines=True)
        if not capped_snapshot:
            return latest_snapshot

        if self._snapshot_line_count(capped_snapshot) < self._snapshot_line_count(latest_snapshot):
            return latest_snapshot

        return capped_snapshot

    @staticmethod
    def _snapshot_depth(snapshot: dict[str, Any] | None) -> int:
        if not snapshot:
            return 0
        return int(snapshot.get("depth", 0) or 0)

    @staticmethod
    def _snapshot_line_count(snapshot: dict[str, Any] | None) -> int:
        if not snapshot:
            return 0
        return len(snapshot.get("lines", []) or [])

    async def _get_job_worker_target_depth(self, fen: str) -> int:
        async with self._jobs_lock:
            job = self._jobs.get(fen)
            return job.worker_target_depth if job else DEFAULT_WORKER_TARGET_DEPTH

    async def _job_is_running(self, fen: str) -> bool:
        async with self._jobs_lock:
            job = self._jobs.get(fen)
            return bool(job and not job.task.done())

    @staticmethod
    def _snapshot_signature(snapshot: dict[str, Any] | None) -> tuple[int, tuple[tuple[int, str | None], ...]] | None:
        if not snapshot:
            return None

        lines = tuple(
            (int(line.get("line_number", 0) or 0), str(line.get("pv") or ""))
            for line in snapshot.get("lines", [])
        )
        return int(snapshot.get("depth", 0) or 0), lines

    @staticmethod
    def _db_enabled() -> bool:
        from app.backend.db.db import DB_ENABLED

        return DB_ENABLED

    async def _send_error(self, websocket: WebSocket, message: str) -> None:
        try:
            await websocket.send_json({"type": "error", "message": message})
        except RuntimeError:
            pass


analysis_coordinator = AnalysisCoordinator()

