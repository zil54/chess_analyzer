import asyncio

import pytest

from app.backend.services.analysis_coordinator import AnalysisCoordinator


class FakeWebSocket:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        return self.payload

    async def send_json(self, payload: dict) -> None:
        self.messages.append(payload)


def _snapshot(depth: int, pv: str = "e2e4 e7e5", line_number: int = 1) -> dict:
    return {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "depth": depth,
        "best_move": "e2e4",
        "score_cp": 25,
        "score_mate": None,
        "pv": pv,
        "lines": [
            {
                "line_number": line_number,
                "best_move": "e2e4",
                "score_cp": 25,
                "score_mate": None,
                "pv": pv,
            }
        ],
    }


def test_parse_request_payload_supports_plain_text_and_json() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    plain_request = AnalysisCoordinator.parse_request_payload(fen)
    assert plain_request.fen == fen
    assert plain_request.display_target_depth == 10
    assert plain_request.worker_target_depth == 70
    assert plain_request.display_lag_depth == 2

    json_request = AnalysisCoordinator.parse_request_payload(
        '{"fen": "' + fen + '", "depth": 18, "worker_target_depth": 24, "display_lag_depth": 3}'
    )
    assert json_request.fen == fen
    assert json_request.display_target_depth == 18
    assert json_request.worker_target_depth == 24
    assert json_request.display_lag_depth == 3


@pytest.mark.asyncio
async def test_ensure_analysis_reuses_existing_job_and_raises_worker_target_depth(monkeypatch) -> None:
    coordinator = AnalysisCoordinator()
    release = asyncio.Event()

    async def fake_run_analysis_job(fen: str) -> None:
        await release.wait()

    monkeypatch.setattr(coordinator, "_run_analysis_job", fake_run_analysis_job)

    started = await coordinator.ensure_analysis("fen-1", 18)
    started_again = await coordinator.ensure_analysis("fen-1", 24)

    assert started is True
    assert started_again is False
    assert coordinator._jobs["fen-1"].worker_target_depth == 24

    release.set()
    await asyncio.gather(*(job.task for job in coordinator._jobs.values()), return_exceptions=True)


@pytest.mark.asyncio
async def test_handle_websocket_extends_cached_snapshot_beyond_requested_worker_target(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 12, "worker_target_depth": 18}'
    )
    started: list[tuple[str, int]] = []
    running_states = iter([True, False])

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False) -> dict:
        if target_depth is None:
            return _snapshot(20)
        return _snapshot(min(target_depth, 20))

    async def fake_ensure_analysis(fen: str, worker_target_depth: int, multipv: int = 3) -> bool:
        started.append((fen, worker_target_depth))
        return True

    async def fake_job_is_running(fen: str) -> bool:
        try:
            return next(running_states)
        except StopIteration:
            return False

    monkeypatch.setattr(coordinator, "get_snapshot", fake_get_snapshot)
    monkeypatch.setattr(coordinator, "ensure_analysis", fake_ensure_analysis)
    monkeypatch.setattr(coordinator, "_job_is_running", fake_job_is_running)

    await coordinator.handle_websocket(websocket)

    assert websocket.accepted is True
    assert started == [("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 26)]
    assert [message["type"] for message in websocket.messages] == ["snapshot", "status", "status"]
    assert websocket.messages[0]["depth"] == 20
    assert websocket.messages[0]["worker_target_depth"] == 26
    assert websocket.messages[0]["worker_running"] is True
    assert websocket.messages[1]["status"] == "analysis_started"
    assert "worker deepens to 26" in websocket.messages[1]["message"]
    assert websocket.messages[-1]["status"] == "complete"
    assert websocket.messages[-1]["worker_depth"] == 20
    assert websocket.messages[-1]["worker_complete"] is False


@pytest.mark.asyncio
async def test_handle_websocket_returns_terminal_cached_snapshot_at_max_depth(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 12, "worker_target_depth": 18}'
    )

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False) -> dict:
        return _snapshot(70)

    async def fail_ensure(*args, **kwargs):
        raise AssertionError("ensure_analysis should not be called for a max-depth cached snapshot")

    monkeypatch.setattr(coordinator, "get_snapshot", fake_get_snapshot)
    monkeypatch.setattr(coordinator, "ensure_analysis", fail_ensure)

    await coordinator.handle_websocket(websocket)

    assert websocket.accepted is True
    assert [message["type"] for message in websocket.messages] == ["snapshot", "status"]
    assert websocket.messages[0]["depth"] == 70
    assert websocket.messages[0]["worker_running"] is False
    assert websocket.messages[1]["status"] == "complete"
    assert websocket.messages[1]["worker_complete"] is True


@pytest.mark.asyncio
async def test_handle_websocket_prefers_richer_snapshot_over_one_line_lagged_snapshot(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 20, "worker_target_depth": 26, "display_lag_depth": 2}'
    )
    running_states = iter([True, False])
    rich_snapshot = {
        **_snapshot(41),
        "lines": [
            {"line_number": 1, "best_move": "e2e4", "score_cp": 30, "score_mate": None, "pv": "e2e4 e7e5"},
            {"line_number": 2, "best_move": "d2d4", "score_cp": 24, "score_mate": None, "pv": "d2d4 d7d5"},
            {"line_number": 3, "best_move": "g1f3", "score_cp": 21, "score_mate": None, "pv": "g1f3 d7d5"},
        ],
    }
    one_line_lagged_snapshot = {
        **_snapshot(39),
        "lines": [
            {"line_number": 1, "best_move": "e2e4", "score_cp": 28, "score_mate": None, "pv": "e2e4 e7e5"},
        ],
    }

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False):
        if target_depth is None:
            return rich_snapshot
        if prefer_richer_lines:
            return rich_snapshot
        return one_line_lagged_snapshot

    async def fake_ensure_analysis(fen: str, worker_target_depth: int, multipv: int = 3) -> bool:
        return False

    async def fake_job_is_running(fen: str) -> bool:
        try:
            return next(running_states)
        except StopIteration:
            return False

    monkeypatch.setattr(coordinator, "get_snapshot", fake_get_snapshot)
    monkeypatch.setattr(coordinator, "ensure_analysis", fake_ensure_analysis)
    monkeypatch.setattr(coordinator, "_job_is_running", fake_job_is_running)

    await coordinator.handle_websocket(websocket)

    snapshot_messages = [message for message in websocket.messages if message["type"] == "snapshot"]
    assert snapshot_messages
    assert len(snapshot_messages[0]["lines"]) == 3
    assert snapshot_messages[0]["depth"] == 41


@pytest.mark.asyncio
async def test_handle_websocket_starts_worker_and_streams_lagged_db_snapshots(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 12, "worker_target_depth": 18, "display_lag_depth": 2}'
    )
    latest_depths = iter([12, 13, 14, 18, 18])
    running_states = iter([True, True, True, False])
    started: list[tuple[str, int]] = []

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False):
        if target_depth is None:
            try:
                depth = next(latest_depths)
            except StopIteration:
                depth = 18
            return _snapshot(depth)

        return _snapshot(min(target_depth, 18))

    async def fake_ensure_analysis(fen: str, worker_target_depth: int, multipv: int = 3) -> bool:
        started.append((fen, worker_target_depth))
        return True

    async def fake_job_is_running(fen: str) -> bool:
        try:
            return next(running_states)
        except StopIteration:
            return False

    monkeypatch.setattr(coordinator, "get_snapshot", fake_get_snapshot)
    monkeypatch.setattr(coordinator, "ensure_analysis", fake_ensure_analysis)
    monkeypatch.setattr(coordinator, "_job_is_running", fake_job_is_running)

    await coordinator.handle_websocket(websocket)

    assert started == [("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 18)]
    assert [message["type"] for message in websocket.messages] == ["snapshot", "status", "snapshot", "snapshot", "status"]
    assert websocket.messages[0]["depth"] == 12
    assert websocket.messages[1]["status"] == "analysis_started"
    assert websocket.messages[2]["depth"] == 16
    assert websocket.messages[2]["worker_depth"] == 18
    assert websocket.messages[3]["depth"] == 18
    assert websocket.messages[3]["worker_running"] is False
    assert websocket.messages[-1]["status"] == "complete"

