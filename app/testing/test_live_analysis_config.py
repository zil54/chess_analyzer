import importlib
import os


def test_backend_live_analysis_env_defaults_are_clamped(monkeypatch) -> None:
    names = [
        "LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH",
        "LIVE_ANALYSIS_WORKER_TARGET_DEPTH",
        "LIVE_ANALYSIS_DISPLAY_LAG_DEPTH",
    ]
    previous = {name: os.environ.get(name) for name in names}

    monkeypatch.setenv("LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH", "19")
    monkeypatch.setenv("LIVE_ANALYSIS_WORKER_TARGET_DEPTH", "999")
    monkeypatch.setenv("LIVE_ANALYSIS_DISPLAY_LAG_DEPTH", "-3")

    import app.backend.config as config

    reloaded = importlib.reload(config)

    assert reloaded.LIVE_ANALYSIS_DISPLAY_TARGET_DEPTH == 19
    assert reloaded.LIVE_ANALYSIS_WORKER_TARGET_DEPTH == 70
    assert reloaded.LIVE_ANALYSIS_DISPLAY_LAG_DEPTH == 0

    for name, value in previous.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    importlib.reload(config)
