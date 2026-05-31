import asyncio
import csv
from datetime import datetime
import os
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.database import get_db as get_session
from app.models.brigade_transaction import BrigadeTransaction

# Correct the path to be relative to the project root
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv')

async def load_brigade_transactions():
    """
    Reads transaction data from the Brigade CSV, validates it, and upserts it into the brigade_transactions table.
    """
    print(f"--- Starting Brigade Transaction Load from {CSV_FILE_PATH} ---")

    if not os.path.exists(CSV_FILE_PATH):
        print(f"ERROR: Dataset not found at {CSV_FILE_PATH}")
        return

    # 1. Read and Validate CSV
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        # Normalize column names (lowercase and replace spaces/special chars with underscores)
        df.columns = [col.lower().replace(' ', '_').replace('(', '').replace(')', '') for col in df.columns]
        
    except Exception as e:
        print(f"ERROR: Failed to read or validate CSV file: {e}")
        return

    # 2. Data Cleaning and Preparation
    df['order_date'] = pd.to_datetime(df['order_date'], format='%d-%m-%Y').dt.date
    df['order_time'] = pd.to_datetime(df['order_time'], format='%H:%M:%S').dt.time
    
    float_cols = {'tax', 'gmv', 'nmv', 'coupon_amount', 'item_promotion', 'amt_without_gwp', 'total_amount', 'tax_m', 'taxable_amt', 'tax_amt'}
    int_cols = {'store_id', 'qty'}
    datetime_cols = {'order_date', 'order_time', 'created_at', 'updated_at', 'id'}

    def clean_val(k, v):
        if pd.isna(v):
            return None
        if k in float_cols:
            try:
                return float(v)
            except ValueError:
                return 0.0
        if k in int_cols:
            if isinstance(v, str):
                digits = ''.join(c for c in v if c.isdigit())
                return int(digits) if digits else 0
            return int(v)
        if k in datetime_cols:
            return v
        
        # All other fields are database strings
        if isinstance(v, float):
            if v.is_integer():
                return str(int(v))
            return str(v)
        return str(v)

    import uuid

    raw_records = df.to_dict(orient='records')
    transactions_to_load = []
    for idx, r in enumerate(raw_records):
        clean_r = {k: clean_val(k, v) for k, v in r.items()}
        # Generate deterministic UUID for each row based on order_id and index
        clean_r['id'] = uuid.uuid5(uuid.NAMESPACE_DNS, f"brigade_{idx}_{clean_r['order_id']}")
        transactions_to_load.append(clean_r)
        
    csv_row_count = len(transactions_to_load)
    print(f"Found {csv_row_count} rows in the CSV file.")

    # 3. Upsert into Database
    db_session_gen = get_session()
    db_session = await anext(db_session_gen)
    try:
        # Use PostgreSQL's ON CONFLICT to perform an upsert
        stmt = insert(BrigadeTransaction).values(transactions_to_load)
        
        # Identify columns to update, excluding the composite primary key
        update_cols = {c.name: c for c in stmt.excluded if c.name != 'order_id' and c.name != 'id'}

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['order_id', 'id'],
            set_=update_cols
        )
        
        await db_session.execute(upsert_stmt)
        await db_session.commit()
    finally:
        await db_session.close()


    # 4. Verify and Print Stats
    db_session_gen = get_session()
    db_session = await anext(db_session_gen)
    try:
        db_row_count_result = await db_session.execute(text("SELECT COUNT(*) FROM brigade_transactions;"))
        db_row_count = db_row_count_result.scalar_one()

        revenue_result = await db_session.execute(text("SELECT SUM(nmv) FROM brigade_transactions;"))
        total_revenue = revenue_result.scalar_one()
    finally:
        await db_session.close()

    print("\n--- Verification ---")
    print(f"CSV Row Count: {csv_row_count}")
    print(f"Database Row Count: {db_row_count}")
    print(f"Total Revenue in DB: {total_revenue:,.2f}")

    if csv_row_count == db_row_count:
        print("\nSUCCESS: CSV row count matches database row count.")
    else:
        print("\nWARNING: Mismatch between CSV and database row counts.")

    print("--- Load Complete ---")


if __name__ == "__main__":
    asyncio.run(load_brigade_transactions())
