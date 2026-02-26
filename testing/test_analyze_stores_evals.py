#!/usr/bin/env python
"""
Simple test to verify /analyze endpoint stores to evals table
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test FEN
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

print("=" * 70)
print("TESTING /analyze ENDPOINT")
print("=" * 70)
print()

# Step 1: Call /analyze
print("Step 1: Calling POST /analyze...")
print(f"  FEN: {STARTING_FEN}")
print()

try:
    response = requests.post(
        f"{BASE_URL}/analyze",
        json={
            "fen": STARTING_FEN,
            "depth": 10,
            "time_limit": 0.5
        },
        timeout=10
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    print()

    if response.status_code == 200:
        print("✓ Analysis successful")
        print(f"  Best move: {data.get('best_move')}")
        print(f"  Score: {data.get('score_cp')}cp")
        print(f"  Depth: {data.get('depth')}")
        print(f"  Cached: {data.get('cached')}")
    else:
        print(f"✗ Analysis failed: {data.get('detail')}")
        exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    print()
    print("Make sure backend is running:")
    print("  python -m app.backend.main")
    exit(1)

print()

# Step 2: Verify in database
print("Step 2: Checking if evaluation was stored in evals table...")
print()

try:
    response = requests.get(
        f"{BASE_URL}/evals",
        params={"fen": STARTING_FEN},
        timeout=5
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Evaluation found in evals table!")
        print(f"  Best move: {data.get('best_move')}")
        print(f"  Score: {data.get('score_cp')}cp")
        print(f"  Depth: {data.get('depth')}")
        print(f"  Created: {data.get('created_at')}")
    elif response.status_code == 404:
        print("✗ Evaluation NOT found in evals table!")
        print("  This means /analyze didn't store the result")
    else:
        print(f"✗ Error: {response.json()}")

except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 70)

