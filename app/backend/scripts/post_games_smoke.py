"""Small smoke script to POST a PGN to the running backend.

Usage (PowerShell):
  python -m app.backend.scripts.post_games_smoke

Expects backend at http://127.0.0.1:8000
"""

from __future__ import annotations

import requests


def main() -> None:
    pgn = (
        '[Event "APITest"]\n'
        '[Site "Local"]\n'
        '[Date "2026.02.21"]\n'
        '[Round "-"]\n'
        '[White "W"]\n'
        '[Black "B"]\n'
        '[Result "*"]\n'
        '\n'
        '1. e4 e5 *\n'
    )

    files = {"file": ("test.pgn", pgn.encode("utf-8"), "application/x-chess-pgn")}
    r = requests.post("http://127.0.0.1:8000/games", files=files, timeout=10)
    print("status", r.status_code)
    print(r.text)


if __name__ == "__main__":
    main()

