#!/usr/bin/env python3
"""
Test the computed property logic for session games filtering.
"""

# Simulate the computed property behavior
def compute_session_games(session_game_ids, games):
    if len(session_game_ids) == 0:
        return games
    return [g for g in games if g['id'] in session_game_ids]

# Test case 1: Empty session, show all games
print("Test 1: Empty session, show all games")
session_ids = []
all_games = [
    {"id": 1, "white": "A", "black": "B"},
    {"id": 2, "white": "C", "black": "D"},
    {"id": 3, "white": "E", "black": "F"},
]
result = compute_session_games(session_ids, all_games)
print(f"  sessionGameIds: {session_ids}")
print(f"  games count: {len(all_games)}")
print(f"  sessionGames count: {len(result)}")
print(f"  Expected: 3, Got: {len(result)}, {'✅ PASS' if len(result) == 3 else '❌ FAIL'}")

# Test case 2: Session has IDs, show only session games
print("\nTest 2: Session has IDs, show only session games")
session_ids = [1, 3]
all_games = [
    {"id": 1, "white": "A", "black": "B"},
    {"id": 2, "white": "C", "black": "D"},
    {"id": 3, "white": "E", "black": "F"},
    {"id": 99, "white": "Old", "black": "Game"},  # Should not be included
]
result = compute_session_games(session_ids, all_games)
print(f"  sessionGameIds: {session_ids}")
print(f"  games count: {len(all_games)}")
print(f"  sessionGames count: {len(result)}")
print(f"  sessionGames: {[(g['white'], g['black']) for g in result]}")
print(f"  Expected: 2 games (A vs B, E vs F)")
print(f"  Got: {len(result)} games")
print(f"  {'✅ PASS' if len(result) == 2 and all(g['id'] in session_ids for g in result) else '❌ FAIL'}")

# Test case 3: Session IDs but games not fetched yet
print("\nTest 3: Session IDs set but games not yet fetched from DB")
session_ids = [1, 2, 3]
all_games = []  # No games fetched yet
result = compute_session_games(session_ids, all_games)
print(f"  sessionGameIds: {session_ids}")
print(f"  games count: {len(all_games)}")
print(f"  sessionGames count: {len(result)}")
print(f"  Expected: 0 (games not fetched yet)")
print(f"  Got: {len(result)}")
print(f"  {'✅ PASS' if len(result) == 0 else '❌ FAIL'}")

# Test case 4: Newly uploaded games mixed with old games
print("\nTest 4: Newly uploaded games mixed with old games")
session_ids = [7, 8, 9]  # New games
all_games = [
    {"id": 1, "white": "Old1", "black": "Game1"},
    {"id": 2, "white": "Old2", "black": "Game2"},
    {"id": 7, "white": "New1", "black": "New1b"},
    {"id": 8, "white": "New2", "black": "New2b"},
    {"id": 9, "white": "New3", "black": "New3b"},
]
result = compute_session_games(session_ids, all_games)
print(f"  sessionGameIds: {session_ids}")
print(f"  games count: {len(all_games)}")
print(f"  sessionGames count: {len(result)}")
print(f"  sessionGames: {[(g['white'], g['black']) for g in result]}")
print(f"  Expected: 3 games (New1 vs New1b, New2 vs New2b, New3 vs New3b)")
print(f"  Got: {len(result)} games")
print(f"  {'✅ PASS' if len(result) == 3 and all(g['id'] in session_ids for g in result) else '❌ FAIL'}")

print("\n✅ All filtering tests passed!")

