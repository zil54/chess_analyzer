#!/usr/bin/env python
"""
Manual test: Upload PGN and check if evals table is populated
Run with backend already running
"""
import requests
import sys
import time

BASE_URL = "http://localhost:8000"

# Simple test PGN
TEST_PGN = """[Event "Test"]
[Site "Test"]
[Date "2026.02.21"]
[White "White"]
[Black "Black"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 *
"""

print("=" * 70)
print("MANUAL PGN UPLOAD TEST")
print("=" * 70)
print()

try:
    print("Step 1: Upload PGN file...")
    files = {'file': ('test.pgn', TEST_PGN.encode('utf-8'), 'application/x-chess-pgn')}

    response = requests.post(f"{BASE_URL}/games", files=files, timeout=30)
    print(f"  Status: {response.status_code}")

    if response.status_code != 200:
        print(f"  Error: {response.text}")
        sys.exit(1)

    data = response.json()
    game_id = data['id']
    total_moves = data['total_moves']

    print(f"  ✓ Game uploaded: ID={game_id}, Moves={total_moves}")
    print()

    print("Step 2: Wait for auto-analysis...")
    time.sleep(3)
    print()

    print("Step 3: Trigger manual batch analysis...")
    response = requests.post(
        f"{BASE_URL}/games/{game_id}/analyze",
        json={"depth": 10, "time_limit": 0.5},
        timeout=60
    )

    print(f"  Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ Analysis complete:")
        print(f"    Analyzed: {result['analyzed']}")
        print(f"    Cached: {result['cached']}")
        print(f"    Time: {result['total_time_seconds']}s")
    else:
        print(f"  Error: {response.text}")

    print()
    print("=" * 70)
    print("Check backend terminal for detailed logs")
    print("=" * 70)

except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("Make sure backend is running:")
    print("  python -m app.backend.main")

