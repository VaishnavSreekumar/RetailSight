
import asyncio
import json
import os
import pandas as pd
from sqlalchemy import text
from app.database import get_db as get_session

MAPPING_FILE_PATH = os.path.join(os.path.dirname(__file__), 'app', 'config', 'brand_to_section_mapping.json')

async def reconcile_and_verify_sections():
    """
    Performs a full reconciliation between the Brigade transaction dataset and the brand-to-section mapping.
    """
    print("--- Starting Sprint 20D: Section Revenue Verification & Reconciliation ---")

    # --- 1. Load Data Sources ---
    db_session_gen = get_session()
    db = await anext(db_session_gen)
    try:
        # Load distinct brands from the database
        brands_in_db_result = await db.execute(text("SELECT DISTINCT brand_name FROM brigade_transactions WHERE brand_name IS NOT NULL;"))
        brands_in_db = {row[0] for row in brands_in_db_result.fetchall()}
        print(f"\nFound {len(brands_in_db)} distinct brands in the database.")

        # Load the mapping file
        if not os.path.exists(MAPPING_FILE_PATH):
            print(f"ERROR: Mapping file not found at {MAPPING_FILE_PATH}")
            return
        with open(MAPPING_FILE_PATH, 'r') as f:
            brand_mappings = json.load(f)
        brands_in_mapping = {item['brand_name'] for item in brand_mappings}
        print(f"Found {len(brands_in_mapping)} brands in the mapping file.")

        # --- 2. Brand Reconciliation ---
        mapped_brands = brands_in_db.intersection(brands_in_mapping)
        unmapped_brands = brands_in_db.difference(brands_in_mapping)
        phantom_brands = brands_in_mapping.difference(brands_in_db)
        
        # Check for duplicate mappings
        seen = set()
        duplicates = {item['brand_name'] for item in brand_mappings if item['brand_name'] in seen or seen.add(item['brand_name'])}

        # --- 3. Coverage Report ---
        coverage_percentage = (len(mapped_brands) / len(brands_in_db)) * 100 if len(brands_in_db) > 0 else 0
        
        print("\n--- Reconciliation Report ---")
        print(f"Total Brands in Dataset: {len(brands_in_db)}")
        print(f"Mapped Brands:           {len(mapped_brands)}")
        print(f"Unmapped Brands:         {len(unmapped_brands)}")
        print(f"Coverage Percentage:     {coverage_percentage:.2f}%")
        
        if unmapped_brands:
            print("\nWARNING: The following brands are in the transaction data but NOT in the mapping file:")
            for brand in sorted(unmapped_brands):
                print(f"  - {brand}")
        
        if phantom_brands:
            print("\nINFO: The following brands are in the mapping file but NOT in the transaction data:")
            for brand in sorted(phantom_brands):
                print(f"  - {brand}")

        if duplicates:
            print("\nERROR: The following brands have duplicate entries in the mapping file:")
            for brand in sorted(duplicates):
                print(f"  - {brand}")
            return # Stop execution if duplicates are found

        # --- 4. Section-Level Metrics Calculation ---
        print("\n--- Section-Level Metrics ---")
        
        # Fetch transactions and construct DataFrame
        query_res = await db.execute(text("SELECT brand_name, gmv, nmv FROM brigade_transactions;"))
        df_transactions = pd.DataFrame([dict(row._mapping) for row in query_res.fetchall()])
        
        # Create a mapping DataFrame
        df_mapping = pd.DataFrame(brand_mappings)
        
        # Merge the two DataFrames
        df_merged = pd.merge(df_transactions, df_mapping, on='brand_name', how='left')
        
        # Group by section and aggregate
        section_metrics = df_merged.groupby('section').agg(
            Revenue_NMV=('nmv', 'sum'),
            Revenue_GMV=('gmv', 'sum'),
            Transaction_Count=('brand_name', 'size'),
            Unique_Brands=('brand_name', 'nunique')
        ).reset_index()
        
        section_metrics['Average_Basket_Value'] = section_metrics['Revenue_NMV'] / section_metrics['Transaction_Count']
        
        print(section_metrics.to_string())

        # --- 5. Final Verification ---
        print("\n--- Final Revenue Reconciliation ---")
        total_section_nmv = section_metrics['Revenue_NMV'].sum()
        
        total_db_nmv_result = await db.execute(text("SELECT SUM(nmv) FROM brigade_transactions;"))
        total_db_nmv = total_db_nmv_result.scalar_one()
        
        print(f"Total Revenue Across Sections (NMV): {total_section_nmv:,.2f}")
        print(f"Total Revenue in Database (NMV):     {total_db_nmv:,.2f}")
        
        if abs(total_section_nmv - total_db_nmv) < 0.01:
            print("\nSUCCESS: Revenue reconciliation passed.")
        else:
            print("\nFAILED: Revenue reconciliation failed. Check for unmapped brands.")

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(reconcile_and_verify_sections())
