import requests
import json

try:
    # Call the /games endpoint to list all games
    response = requests.get('http://127.0.0.1:8000/games', timeout=10)
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response:\n{json.dumps(result, indent=2)}")

    if result.get('total_games', 0) > 0:
        print(f"\n✓ SUCCESS: Retrieved {result['total_games']} games from the database")
        print("\nFirst 3 games:")
        for game in result['games'][:3]:
            print(f"  - ID: {game['id']}, {game['white']} vs {game['black']} ({game['result']})")
    else:
        print(f"\n⚠ WARNING: No games found in database")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

