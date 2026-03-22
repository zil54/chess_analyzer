import asyncio
import importlib

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


def test_cache_unlock_depth_delta_is_configurable_via_backend_env(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA", "5")

    import app.backend.config as config
    import app.backend.services.analysis_coordinator as analysis_coordinator_module

    importlib.reload(config)
    reloaded = importlib.reload(analysis_coordinator_module)

    try:
        request = reloaded.AnalysisCoordinator.parse_request_payload(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
        event = reloaded.AnalysisCoordinator.build_snapshot_event(
            _snapshot(18),
            request,
            source="database",
            worker_depth=20,
            worker_running=True,
            cached_depth=18,
        )

        assert reloaded.DEFAULT_CACHE_UNLOCK_DEPTH_DELTA == 5
        assert event["display_unlock_depth"] == 23
        assert event["display_locked"] is True
    finally:
        monkeypatch.delenv("LIVE_ANALYSIS_CACHE_UNLOCK_DEPTH_DELTA", raising=False)
        importlib.reload(config)
        importlib.reload(analysis_coordinator_module)


def test_build_snapshot_event_without_cached_depth_is_not_locked() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    request = AnalysisCoordinator.parse_request_payload(fen)

    event = AnalysisCoordinator.build_snapshot_event(
        _snapshot(4),
        request,
        source="engine",
        worker_depth=6,
        worker_running=True,
        cached_depth=None,
    )

    assert event["source"] == "engine"
    assert event["cached_depth"] is None
    assert event["display_unlock_depth"] is None
    assert event["display_locked"] is False
    assert event["background_analysis"] is False


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
    assert websocket.messages[0]["cached_depth"] == 20
    assert websocket.messages[0]["display_unlock_depth"] == 23
    assert websocket.messages[0]["display_locked"] is True
    assert websocket.messages[1]["status"] == "analysis_started"
    assert "app analyzes further" in websocket.messages[1]["message"]
    assert websocket.messages[1]["display_locked"] is True
    assert websocket.messages[-1]["status"] == "complete"
    assert websocket.messages[-1]["worker_depth"] == 20
    assert websocket.messages[-1]["worker_complete"] is False
    assert websocket.messages[-1]["display_locked"] is False


@pytest.mark.asyncio
async def test_handle_websocket_holds_cached_snapshot_until_worker_reaches_cached_depth_plus_three(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 10, "worker_target_depth": 30, "display_lag_depth": 2}'
    )
    latest_depths = iter([18, 19, 20, 21, 22])
    running_states = iter([True, True, True, False])

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False):
        if target_depth is None:
            try:
                depth = next(latest_depths)
            except StopIteration:
                depth = 22
            return _snapshot(depth)

        return _snapshot(min(target_depth, 22))

    async def fake_ensure_analysis(fen: str, worker_target_depth: int, multipv: int = 3) -> bool:
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

    snapshot_messages = [message for message in websocket.messages if message["type"] == "snapshot"]
    progress_statuses = [
        message
        for message in websocket.messages
        if message["type"] == "status" and message["status"] == "analysis_running"
    ]
    assert [message["depth"] for message in snapshot_messages] == [18, 19, 22]
    assert [message["worker_depth"] for message in progress_statuses] == [19, 20]
    assert all(message["display_depth"] == 18 for message in progress_statuses)
    assert all(message["display_locked"] is True for message in progress_statuses)
    assert snapshot_messages[0]["display_locked"] is True
    assert snapshot_messages[0]["display_unlock_depth"] == 21
    assert snapshot_messages[1]["worker_depth"] == 21
    assert snapshot_messages[1]["display_locked"] is False
    assert snapshot_messages[2]["worker_running"] is False


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
    assert websocket.messages[0]["display_locked"] is False
    assert websocket.messages[1]["status"] == "complete"
    assert websocket.messages[1]["worker_complete"] is True
    assert websocket.messages[1]["display_locked"] is False


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

    progress_statuses = [
        message
        for message in websocket.messages
        if message["type"] == "status" and message["status"] == "analysis_running"
    ]

    assert started == [("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 18)]
    assert [message["type"] for message in websocket.messages] == ["snapshot", "status", "status", "status", "snapshot", "snapshot", "status"]
    assert websocket.messages[0]["depth"] == 12
    assert websocket.messages[0]["display_locked"] is True
    assert websocket.messages[0]["display_unlock_depth"] == 15
    assert websocket.messages[1]["status"] == "analysis_started"
    assert websocket.messages[1]["display_locked"] is True
    assert [message["worker_depth"] for message in progress_statuses] == [13, 14]
    assert all(message["display_depth"] == 12 for message in progress_statuses)
    assert all(message["display_locked"] is True for message in progress_statuses)
    assert websocket.messages[4]["depth"] == 16
    assert websocket.messages[4]["worker_depth"] == 18
    assert websocket.messages[4]["display_locked"] is False
    assert websocket.messages[5]["depth"] == 18
    assert websocket.messages[5]["worker_running"] is False
    assert websocket.messages[-1]["status"] == "complete"
    assert websocket.messages[-1]["display_locked"] is False


@pytest.mark.asyncio
async def test_handle_websocket_reports_worker_progress_while_cached_depth_is_locked(monkeypatch) -> None:
    coordinator = AnalysisCoordinator(poll_interval=0)
    websocket = FakeWebSocket(
        '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "depth": 10, "worker_target_depth": 70, "display_lag_depth": 2}'
    )
    latest_depths = iter([40, 41, 42, 43])
    running_states = iter([True, True, False])

    monkeypatch.setattr(coordinator, "_db_enabled", lambda: True)

    async def fake_get_snapshot(fen: str, target_depth: int | None = None, prefer_richer_lines: bool = False):
        if target_depth is None:
            try:
                depth = next(latest_depths)
            except StopIteration:
                depth = 43
            return _snapshot(depth)

        return _snapshot(min(target_depth, 43))

    async def fake_ensure_analysis(fen: str, worker_target_depth: int, multipv: int = 3) -> bool:
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

    snapshot_messages = [message for message in websocket.messages if message["type"] == "snapshot"]
    progress_statuses = [
        message
        for message in websocket.messages
        if message["type"] == "status" and message["status"] == "analysis_running"
    ]

    assert [message["depth"] for message in snapshot_messages] == [40, 43]
    assert snapshot_messages[0]["display_locked"] is True
    assert snapshot_messages[0]["display_unlock_depth"] == 43
    assert [message["worker_depth"] for message in progress_statuses] == [41, 42]
    assert all(message["display_depth"] == 40 for message in progress_statuses)
    assert all(message["display_locked"] is True for message in progress_statuses)
    assert websocket.messages[-2]["type"] == "snapshot"
    assert websocket.messages[-2]["worker_running"] is False
    assert websocket.messages[-1]["status"] == "complete"
    assert websocket.messages[-1]["worker_depth"] == 43


