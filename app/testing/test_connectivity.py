import socket
import requests

print("Testing connectivity...")

# Test basic socket connection
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8000))
    if result == 0:
        print("✓ Port 8000 is open")
    else:
        print("✗ Port 8000 is closed")
    sock.close()
except Exception as e:
    print(f"✗ Socket error: {e}")

# Test health check endpoint
try:
    response = requests.get('http://127.0.0.1:8000/health/db', timeout=5)
    print(f"✓ Health check response: {response.status_code}")
    print(f"  {response.json()}")
except Exception as e:
    print(f"✗ Health check failed: {e}")

# Test /games endpoint
try:
    response = requests.get('http://127.0.0.1:8000/games', timeout=5)
    print(f"✓ /games endpoint response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Games: {data.get('total_games', 'unknown')} total")
    else:
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"✗ /games endpoint failed: {e}")

