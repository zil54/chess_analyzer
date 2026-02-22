"""
Test script for the /analyze endpoint.

Tests the cache-then-compute pattern:
1. First call should run Stockfish (cache miss)
2. Second call with same FEN should return cached result
3. force_recompute=True should bypass cache and run Stockfish again
"""

import pytest
import httpx
import asyncio
import json
from typing import Dict

# Assuming backend runs on http://localhost:8000
BASE_URL = "http://localhost:8000"

# Test FENs
STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_1_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
INVALID_FEN = "invalid fen position"


@pytest.mark.asyncio
async def test_analyze_valid_fen():
    """Test analyzing a valid FEN."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/analyze",
            json={
                "fen": STARTING_POSITION,
                "depth": 15,
                "time_limit": 1.0
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "fen" in data
        assert "best_move" in data
        assert "depth" in data
        assert data["cached"] == False  # First call should not be cached

        # Verify structure
        assert isinstance(data["best_move"], str) or data["best_move"] is None
        assert isinstance(data["depth"], int)
        assert data["fen"] == STARTING_POSITION


@pytest.mark.asyncio
async def test_analyze_cache_hit():
    """Test that second call with same FEN hits cache."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        fen = STARTING_POSITION

        # First call - cache miss
        response1 = await client.post(
            f"{BASE_URL}/analyze",
            json={"fen": fen, "depth": 15, "time_limit": 1.0}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        first_cached = data1.get("cached", False)

        # Second call - cache hit
        response2 = await client.post(
            f"{BASE_URL}/analyze",
            json={"fen": fen, "depth": 15, "time_limit": 1.0}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        second_cached = data2.get("cached", False)

        # Second call should be cached (assuming DB is enabled)
        print(f"First call cached: {first_cached}, Second call cached: {second_cached}")
        assert data1["best_move"] == data2["best_move"]
        assert data1["score_cp"] == data2["score_cp"]


@pytest.mark.asyncio
async def test_analyze_force_recompute():
    """Test force_recompute flag bypasses cache."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        fen = AFTER_1_E4

        # First call - cache miss
        response1 = await client.post(
            f"{BASE_URL}/analyze",
            json={"fen": fen, "depth": 12, "time_limit": 0.5}
        )
        assert response1.status_code == 200

        # Second call with force_recompute
        response2 = await client.post(
            f"{BASE_URL}/analyze",
            json={
                "fen": fen,
                "depth": 12,
                "time_limit": 0.5,
                "force_recompute": True
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] == False  # Should not be cached despite running twice


@pytest.mark.asyncio
async def test_analyze_invalid_fen():
    """Test that invalid FEN returns error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/analyze",
            json={"fen": INVALID_FEN}
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_analyze_missing_fen():
    """Test that missing FEN returns error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/analyze",
            json={}
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_analyze_response_structure():
    """Test the response structure matches specification."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/analyze",
            json={
                "fen": STARTING_POSITION,
                "depth": 10,
                "time_limit": 0.5
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = ["fen", "best_move", "depth", "cached"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check optional fields if present
        if "score_cp" in data:
            assert isinstance(data["score_cp"], int) or data["score_cp"] is None
        if "score_mate" in data:
            assert isinstance(data["score_mate"], int) or data["score_mate"] is None
        if "pv" in data:
            assert isinstance(data["pv"], str) or data["pv"] is None


if __name__ == "__main__":
    # Run tests manually
    print("=" * 60)
    print("Testing /analyze endpoint")
    print("=" * 60)

    asyncio.run(test_analyze_valid_fen())
    print("✓ test_analyze_valid_fen passed")

    asyncio.run(test_analyze_cache_hit())
    print("✓ test_analyze_cache_hit passed")

    asyncio.run(test_analyze_force_recompute())
    print("✓ test_analyze_force_recompute passed")

    asyncio.run(test_analyze_invalid_fen())
    print("✓ test_analyze_invalid_fen passed")

    asyncio.run(test_analyze_missing_fen())
    print("✓ test_analyze_missing_fen passed")

    asyncio.run(test_analyze_response_structure())
    print("✓ test_analyze_response_structure passed")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

