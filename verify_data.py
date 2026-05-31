
import asyncio
from sqlalchemy import text
from app.database import get_db as get_session

async def verify_brigade_data():
    """Connects to the database and runs verification queries against the brigade_transactions table."""
    
    print("--- Verifying Data in brigade_transactions Table ---")
    
    db_session_gen = get_session()
    db = await anext(db_session_gen)
    try:
        # Query 1: First 20 rows
        print("\n--- First 20 Rows ---")
        query1 = text("""
            SELECT product_name, brand_name, offer_name, salesperson_name
            FROM brigade_transactions
            LIMIT 20;
        """)
        result1 = await db.execute(query1)
        rows = result1.fetchall()
        print(f"{'Product Name':<40} | {'Brand Name':<20} | {'Offer Name':<30} | {'Salesperson Name'}")
        print("-" * 120)
        for row in rows:
            print(f"{str(row[0]):<40} | {str(row[1]):<20} | {str(row[2]):<30} | {str(row[3])}")

        # Query 2: Distinct Brand Names
        print("\n--- Distinct Brand Names ---")
        query2 = text("""
            SELECT DISTINCT brand_name
            FROM brigade_transactions
            ORDER BY brand_name;
        """)
        result2 = await db.execute(query2)
        brands = result2.scalars().all()
        for brand in brands:
            print(brand)

        # Query 3: Distinct Offer Names
        print("\n--- Distinct Offer Names ---")
        query3 = text("""
            SELECT DISTINCT offer_name
            FROM brigade_transactions
            ORDER BY offer_name;
        """)
        result3 = await db.execute(query3)
        offers = result3.scalars().all()
        for offer in offers:
            print(offer)

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(verify_brigade_data())
