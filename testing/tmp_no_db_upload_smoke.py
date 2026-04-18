from fastapi.testclient import TestClient
from app.backend.main import app

VALID_PGN = """[Event \"Test\"]
[Site \"Local\"]
[Date \"2026.03.10\"]
[Round \"-\"]
[White \"WhitePlayer\"]
[Black \"BlackPlayer\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 1-0
"""

INVALID_PGN = "not a real pgn"

with TestClient(app) as client:
    ok = client.post(
        "/games",
        files={"file": ("game.pgn", VALID_PGN.encode("utf-8"), "application/x-chess-pgn")},
    )
    print("OK_STATUS", ok.status_code)
    ok_json = ok.json()
    print("OK_ID", ok_json.get("id"))
    print("OK_TOTAL_MOVES", ok_json.get("total_moves"))
    print("OK_POSITIONS_LEN", len(ok_json.get("positions", [])))

    bad = client.post(
        "/games",
        files={"file": ("bad.pgn", INVALID_PGN.encode("utf-8"), "application/x-chess-pgn")},
    )
    print("BAD_STATUS", bad.status_code)
    print("BAD_DETAIL", bad.json().get("detail"))

