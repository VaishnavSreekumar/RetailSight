
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

# Connection details from app/config.py
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/retail_intelligence"

async def run_queries():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        print("--- Database Record Counts ---")
        
        # 1. Count events
        try:
            result_events = await conn.execute(text("SELECT COUNT(*) FROM events;"))
            count_events = result_events.scalar_one()
            print(f"SELECT COUNT(*) FROM events; -> {count_events}")
        except Exception as e:
            print(f"Error querying 'events': Table likely does not exist. Full error: {e}")

        # 2. Count visitor_sessions
        try:
            result_sessions = await conn.execute(text("SELECT COUNT(*) FROM visitor_sessions;"))
            count_sessions = result_sessions.scalar_one()
            print(f"SELECT COUNT(*) FROM visitor_sessions; -> {count_sessions}")
        except Exception as e:
            print(f"Error querying 'visitor_sessions': Table likely does not exist. Full error: {e}")

        # 3. Count transactions (original empty table)
        try:
            result_transactions = await conn.execute(text("SELECT COUNT(*) FROM transactions;"))
            count_transactions = result_transactions.scalar_one()
            print(f"SELECT COUNT(*) FROM transactions; -> {count_transactions}")
        except Exception as e:
            print(f"Error querying 'transactions': {e}")

        # 4. Count brigade_transactions (the real data)
        try:
            result_brigade = await conn.execute(text("SELECT COUNT(*) FROM brigade_transactions;"))
            count_brigade = result_brigade.scalar_one()
            print(f"SELECT COUNT(*) FROM brigade_transactions; -> {count_brigade}")
        except Exception as e:
            print(f"Error querying 'brigade_transactions': {e}")

if __name__ == "__main__":
    asyncio.run(run_queries())
