import asyncio
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def check_db():
    print("Starting database check...")
    try:
        print("Importing database module...")
        from app.backend.db.db import get_connection, DB_ENABLED

        print(f"DB_ENABLED: {DB_ENABLED}")
        if not DB_ENABLED:
            print("ERROR: Database not enabled")
            return

        conn = await get_connection()
        async with conn.cursor() as cur:
            # Check games table
            await cur.execute("SELECT COUNT(*) as count FROM public.games")
            games_count = await cur.fetchone()
            print(f"Games in DB: {games_count['count']}")

            # Check moves table
            await cur.execute("SELECT COUNT(*) as count FROM public.moves")
            moves_count = await cur.fetchone()
            print(f"Moves in DB: {moves_count['count']}")

            # Show recent games
            await cur.execute("""
                SELECT id, white, black, result, event 
                FROM public.games 
                ORDER BY id DESC 
                LIMIT 5
            """)
            games = await cur.fetchall()
            print(f"\nRecent games:")
            for game in games:
                print(f"  ID: {game['id']}, White: {game['white']}, Black: {game['black']}, Event: {game['event']}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Database check complete.")

# Run async
print("Setting event loop policy...")
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

print("Running check_db...")
asyncio.run(check_db())
print("Done.")



