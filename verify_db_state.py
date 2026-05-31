import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    """Connects to the database and executes a series of read-only queries."""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/retail_intelligence",
        echo=False,
    )

    async with engine.connect() as conn:
        print("--- Contents of alembic_version table ---")
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        for row in result:
            print(row[0])

        print("\n--- Record Counts ---")
        count_events = await conn.execute(text("SELECT COUNT(*) FROM events"))
        print(f"SELECT COUNT(*) FROM events; => {count_events.scalar_one()}")

        count_sessions = await conn.execute(text("SELECT COUNT(*) FROM visitor_sessions"))
        print(f"SELECT COUNT(*) FROM visitor_sessions; => {count_sessions.scalar_one()}")

        print("\n--- Raw rows from events (LIMIT 20) ---")
        result_events = await conn.execute(text("SELECT * FROM events LIMIT 20"))
        for row in result_events:
            print(dict(row._mapping))

        print("\n--- Raw rows from visitor_sessions (LIMIT 20) ---")
        result_sessions = await conn.execute(text("SELECT * FROM visitor_sessions LIMIT 20"))
        for row in result_sessions:
            print(dict(row._mapping))

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
