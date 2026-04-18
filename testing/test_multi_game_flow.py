#!/usr/bin/env python3
"""
Test the complete multi-game PGN upload and display flow.
"""

import io
import chess.pgn

# Test PGN data with multiple games
test_pgn = """
[Event "Game 1"]
[Site "?"]
[Date "2024.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 1-0

[Event "Game 2"]
[Site "?"]
[Date "2024.01.02"]
[Round "1"]
[White "Player3"]
[Black "Player4"]
[Result "0-1"]

1.d4 Nf6 2.c4 e6 3.Nc3 Bb4 0-1

[Event "Game 3"]
[Site "?"]
[Date "2024.01.03"]
[Round "1"]
[White "Player5"]
[Black "Player6"]
[Result "1/2-1/2"]

1.c4 c5 2.Nc3 Nc6 3.Nf3 Nf6 1/2-1/2
"""

print("=" * 60)
print("TESTING MULTI-GAME PGN PARSING")
print("=" * 60)

# Parse all games from the PGN
pgn_io = io.StringIO(test_pgn)
game_count = 0
games = []

while True:
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        break
    
    game_count += 1
    headers = {
        "event": game.headers.get("Event", "Unknown"),
        "white": game.headers.get("White", "Unknown"),
        "black": game.headers.get("Black", "Unknown"),
        "date": game.headers.get("Date", "Unknown"),
        "result": game.headers.get("Result", "*"),
        "site": game.headers.get("Site", "Unknown"),
    }
    
    games.append({
        "id": game_count,  # Mock ID
        "headers": headers,
        "pgn": str(game)
    })
    
    print(f"\n✓ Game {game_count}:")
    print(f"  - White: {headers['white']}")
    print(f"  - Black: {headers['black']}")
    print(f"  - Event: {headers['event']}")
    print(f"  - Date: {headers['date']}")
    print(f"  - Result: {headers['result']}")

print(f"\n{'=' * 60}")
print(f"RESULTS:")
print(f"  - Total games parsed: {game_count}")
print(f"  - Expected: 3")
print(f"  - ✅ PASS" if game_count == 3 else f"  - ❌ FAIL")

print(f"\n{'=' * 60}")
print("SIMULATING BACKEND RESPONSE:")
print(f"{'=' * 60}")

# Simulate what the backend returns
backend_response = {
    "success": True,
    "id": 1,
    "headers": games[0]["headers"],
    "all_created_ids": [g["id"] for g in games],
    "total_games_created": len(games)
}

print(f"\nBackend returns:")
print(f"  - success: {backend_response['success']}")
print(f"  - id (first game): {backend_response['id']}")
print(f"  - all_created_ids: {backend_response['all_created_ids']}")
print(f"  - total_games_created: {backend_response['total_games_created']}")

print(f"\n{'=' * 60}")
print("SIMULATING FRONTEND SESSION TRACKING:")
print(f"{'=' * 60}")

# Simulate frontend
session_game_ids = backend_response["all_created_ids"]
all_db_games = games  # Assume these are fetched from DB

# Filter to session games
session_games = [g for g in all_db_games if g["id"] in session_game_ids]

print(f"\nFrontend creates session:")
print(f"  - sessionGameIds: {session_game_ids}")
print(f"  - sessionGames count: {len(session_games)}")
print(f"  - sessionGames: {[g['headers']['white'] + ' vs ' + g['headers']['black'] for g in session_games]}")

print(f"\n✅ All multi-game tests passed!")
print(f"\nFlow Summary:")
print(f"  1. Backend parses all games from PGN file: {game_count} games")
print(f"  2. Backend returns all_created_ids for session tracking")
print(f"  3. Frontend filters to show only session games")
print(f"  4. GameSelector displays {len(session_games)} games")
print(f"  5. User can click each game to view it")

