"""
Quick manual test for /analyze endpoint

Run this script to test the Stockfish integration:
    python testing/test_analyze_manual.py

Prerequisites:
    1. Backend running: python -m app.backend.main
    2. Database configured in .env (optional, but recommended for caching)
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"

STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_1_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"


def test_endpoint():
    """Test the /analyze endpoint."""

    print("=" * 70)
    print("Testing Chess Analyzer /analyze Endpoint")
    print("=" * 70)
    print()

    # Test 1: Analyze starting position
    print("TEST 1: Analyze starting position (first time - cache miss)")
    print("-" * 70)

    try:
        with httpx.Client(timeout=30.0) as client:
            start = time.time()
            response = client.post(
                f"{BASE_URL}/analyze",
                json={
                    "fen": STARTING_POSITION,
                    "depth": 15,
                    "time_limit": 1.0
                }
            )
            elapsed = time.time() - start

            print(f"Status: {response.status_code}")
            print(f"Time taken: {elapsed:.2f}s")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response structure:")
                print(f"  - FEN: {data.get('fen')[:50]}...")
                print(f"  - Best move: {data.get('best_move')}")
                print(f"  - Score (cp): {data.get('score_cp')}")
                print(f"  - Depth: {data.get('depth')}")
                print(f"  - Cached: {data.get('cached')}")
                print(f"  - PV: {data.get('pv', '')[:50]}...")
            else:
                print(f"✗ Error: {response.text}")

    except Exception as e:
        print(f"✗ Connection error: {e}")
        print(f"  Make sure backend is running: python -m app.backend.main")
        return False

    print()

    # Test 2: Analyze same position again (cache hit)
    print("TEST 2: Analyze same position again (cache hit)")
    print("-" * 70)

    try:
        with httpx.Client(timeout=30.0) as client:
            start = time.time()
            response = client.post(
                f"{BASE_URL}/analyze",
                json={
                    "fen": STARTING_POSITION,
                    "depth": 15,
                    "time_limit": 1.0
                }
            )
            elapsed = time.time() - start

            print(f"Status: {response.status_code}")
            print(f"Time taken: {elapsed:.2f}s")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response:")
                print(f"  - Cached: {data.get('cached')}")
                print(f"  - Best move: {data.get('best_move')}")

                if data.get('cached'):
                    print(f"✓ CACHE HIT! Second call much faster than first.")
                else:
                    print(f"⚠ Cache not working (DB may not be configured)")
                    print(f"  Set DATABASE_URL in .env to enable caching")
            else:
                print(f"✗ Error: {response.text}")

    except Exception as e:
        print(f"✗ Connection error: {e}")

    print()

    # Test 3: Different position
    print("TEST 3: Analyze different position (after 1.e4)")
    print("-" * 70)

    try:
        with httpx.Client(timeout=30.0) as client:
            start = time.time()
            response = client.post(
                f"{BASE_URL}/analyze",
                json={
                    "fen": AFTER_1_E4,
                    "depth": 12,
                    "time_limit": 0.5
                }
            )
            elapsed = time.time() - start

            print(f"Status: {response.status_code}")
            print(f"Time taken: {elapsed:.2f}s")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response:")
                print(f"  - Best move: {data.get('best_move')}")
                print(f"  - Score (cp): {data.get('score_cp')}")
                print(f"  - Depth: {data.get('depth')}")
                print(f"  - Cached: {data.get('cached')}")
            else:
                print(f"✗ Error: {response.text}")

    except Exception as e:
        print(f"✗ Connection error: {e}")

    print()

    # Test 4: Force recompute
    print("TEST 4: Force recompute (bypass cache)")
    print("-" * 70)

    try:
        with httpx.Client(timeout=30.0) as client:
            start = time.time()
            response = client.post(
                f"{BASE_URL}/analyze",
                json={
                    "fen": STARTING_POSITION,
                    "depth": 15,
                    "time_limit": 1.0,
                    "force_recompute": True
                }
            )
            elapsed = time.time() - start

            print(f"Status: {response.status_code}")
            print(f"Time taken: {elapsed:.2f}s")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Response:")
                print(f"  - Best move: {data.get('best_move')}")
                print(f"  - Cached: {data.get('cached')}")

                if not data.get('cached'):
                    print(f"✓ Force recompute worked (bypassed cache)")
                else:
                    print(f"⚠ Unexpected: Should not be cached with force_recompute")
            else:
                print(f"✗ Error: {response.text}")

    except Exception as e:
        print(f"✗ Connection error: {e}")

    print()

    # Test 5: Invalid FEN
    print("TEST 5: Invalid FEN (error handling)")
    print("-" * 70)

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{BASE_URL}/analyze",
                json={"fen": "invalid fen"}
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 400:
                print(f"✓ Correctly rejected invalid FEN")
            else:
                print(f"✗ Expected 400, got {response.status_code}")

    except Exception as e:
        print(f"✗ Connection error: {e}")

    print()
    print("=" * 70)
    print("Test completed!")
    print("=" * 70)
    print()
    print("Summary:")
    print("- /analyze endpoint should work with valid FENs")
    print("- Second call with same FEN should be cached (if DB enabled)")
    print("- force_recompute=true should skip cache")
    print("- Invalid FENs should return 400 error")
    print()
    print("For more info, see: documentation/STOCKFISH_INTEGRATION.md")

    return True


if __name__ == "__main__":
    test_endpoint()

