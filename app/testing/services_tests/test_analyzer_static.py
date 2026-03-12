import pytest

from app.backend.services import analyzer_service

session_command_logs = []


class _FakeProcess:
    def poll(self):
        return None

    def terminate(self):
        return None

    def wait(self, timeout=None):
        return 0

    def kill(self):
        return None


class _FakeSession:
    def __init__(self, path):
        self.path = path
        self.commands = []
        self.process = _FakeProcess()
        self._lines = iter([
            "id name Stockfish",
            "uciok",
            "readyok",
            "info depth 15 multipv 1 score cp 34 nodes 123 pv e2e4 e7e5 g1f3",
            "bestmove e2e4",
        ])
        session_command_logs.append(self.commands)

    def send(self, command: str):
        self.commands.append(command)

    def read_lines(self):
        for line in self._lines:
            yield line


@pytest.mark.asyncio
async def test_analyze_position_returns_structured_error_for_invalid_fen():
    result = await analyzer_service.analyze_position("not a fen")

    assert result["fen"] == "not a fen"
    assert result["cached"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_analyze_position_falls_back_to_direct_stockfish_session(monkeypatch):
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    session_command_logs.clear()

    class _FakeSimpleEngine:
        @staticmethod
        def popen_uci(path):
            raise NotImplementedError

    monkeypatch.setattr(analyzer_service, "DB_ENABLED", False)
    monkeypatch.setattr(analyzer_service, "get_stockfish_path", lambda: "fake-stockfish")
    monkeypatch.setattr(analyzer_service.chess.engine, "SimpleEngine", _FakeSimpleEngine)
    monkeypatch.setattr(analyzer_service, "StockfishSession", _FakeSession)

    result = await analyzer_service.analyze_position(fen, depth=15, time_limit=1.0, force_recompute=True)

    assert result == {
        "fen": fen,
        "best_move": "e2e4",
        "score_cp": 34,
        "score_mate": None,
        "depth": 15,
        "pv": "e2e4 e7e5 g1f3",
        "cached": False,
    }

    assert session_command_logs, "fallback Stockfish session was not used"
    latest_commands = next(reversed(session_command_logs))
    assert "uci" in latest_commands
    assert "isready" in latest_commands
    assert any(command.startswith("go depth 15 movetime 1000") for command in latest_commands)
