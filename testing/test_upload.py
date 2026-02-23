import requests
import json

# Create a test PGN
pgn_content = """[Event "Test Game"]
[Site "Local"]
[Date "2026.02.21"]
[Round "-"]
[White "White Player"]
[Black "Black Player"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 *
"""

# Prepare file for multipart upload
files = {'file': ('test.pgn', pgn_content.encode('utf-8'), 'application/x-chess-pgn')}

try:
    # Call the /analyze_pgn endpoint (which should now persist to DB)
    response = requests.post('http://127.0.0.1:8000/analyze_pgn', files=files, timeout=10)
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")

    if result.get('game_id'):
        print(f"\n✓ SUCCESS: Game persisted to DB with ID: {result['game_id']}")
    else:
        print(f"\n⚠ WARNING: No game_id returned, DB persistence may have failed")

except Exception as e:
    print(f"Error: {e}")

