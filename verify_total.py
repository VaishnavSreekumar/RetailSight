
import pandas as pd
from sqlalchemy import create_engine, text

def get_db_revenue_total():
    """Connects to the database and gets the sum of NMV."""
    engine = create_engine("sqlite:///:memory:")
    
    # Load data into a temporary in-memory DB, same as the test fixture
    csv_path = "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv"
    df = pd.read_csv(csv_path)
    
    # Correcting potential column name mismatches from different CSV versions
    if 'Order ID' in df.columns:
        df = df.rename(columns={
            'Order ID': 'order_id',
            'Brand Name': 'brand_name',
            'NMV': 'nmv',
            'GMV': 'gmv'
        })

    df.to_sql("brigade_transactions", engine, if_exists="replace", index=False)

    with engine.connect() as connection:
        result = connection.execute(text("SELECT SUM(nmv) FROM brigade_transactions;"))
        total_nmv = result.scalar()
        print(f"DATABASE_NMV_TOTAL:{total_nmv}")

if __name__ == "__main__":
    get_db_revenue_total()
