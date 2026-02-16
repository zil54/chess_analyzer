# testing/conftest.py
import sys
import asyncio
import sys, asyncio, os
import pytest_asyncio
import psycopg
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Check your .env file.")

print(DATABASE_URL)

@pytest_asyncio.fixture(scope="session")
async def db_conn():
    """
    Provide a shared async connection for the test session.
    """
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        yield conn



@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_schema(db_conn):
    """
    Drop and recreate schema before tests.
    """
    async with db_conn.cursor() as cur:
        # Drop existing tables
        await cur.execute("DROP SCHEMA public CASCADE;")
        await cur.execute("CREATE SCHEMA public;")

        # Recreate tables (example, adjust to your models)
        await cur.execute("""
            CREATE TABLE session_analysis (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            );
        """)
        await cur.execute("""
            CREATE TABLE analysis_lines (
                id SERIAL PRIMARY KEY,
                session_id INT REFERENCES session_analysis(id),
                line TEXT NOT NULL
            );
        """)
        await db_conn.commit()
    yield
