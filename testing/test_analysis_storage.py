#!/usr/bin/env python
"""
Quick test - start backend and verify analysis_lines gets populated
"""
import subprocess
import asyncio
import sys
import time
sys.path.insert(0, '..')

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

print("=" * 80)
print("TESTING ANALYSIS_LINES STORAGE")
print("=" * 80)
print()

# Check before
print("Checking analysis_lines before test...")
async def check_db():
    from app.backend.db.db import get_connection

    conn = await get_connection()
    async with conn.cursor() as cur:
        await cur.execute("SELECT COUNT(*) as cnt FROM analysis_lines;")
        result = await cur.fetchone()
        count = result['cnt'] if result else 0
    await conn.close()
    return count

before = asyncio.run(check_db())
print(f"Rows before: {before}")
print()

print("To test the fix:")
print("1. Start backend: python -m app.backend.main")
print("2. Open http://localhost:8000")
print("3. Click 'Analyze'")
print("4. Wait for depth >= 15")
print("5. Run this script again to check")
print()
print("Then run: python check_analysis_lines_simple.py")

