"""
This test module automates the verification of section-level revenue reconciliation.
"""
import json
import os
import pytest
import pandas as pd
from sqlalchemy.orm import Session
from app.models.brigade_transaction import BrigadeTransaction
from app.config import BRAND_TO_SECTION_MAPPING_PATH

@pytest.mark.asyncio
async def test_section_revenue_reconciliation(test_db: Session):
    """
    Ensures that the brand-to-section mapping fully accounts for all revenue
    in the brigade_transactions table.

    This test performs two key checks:
    1.  **Coverage Check**: Verifies that every brand in the transaction data is
        present in the mapping file.
    2.  **Revenue Check**: Confirms that the sum of NMV revenue across all mapped
        sections equals the total NMV revenue in the database.
    """
    # 1. Load Data from Database and Mapping File
    from sqlalchemy import select
    res = await test_db.execute(select(BrigadeTransaction))
    db_transactions = res.scalars().all()
    assert db_transactions, "Database contains no BrigadeTransaction data to test."

    with open(BRAND_TO_SECTION_MAPPING_PATH, 'r') as f:
        brand_mapping_list = json.load(f)

    # 2. Create DataFrames for Analysis
    df_transactions = pd.DataFrame([t.__dict__ for t in db_transactions])
    df_mapping = pd.DataFrame(brand_mapping_list)

    # 3. Perform Coverage Check
    brands_in_db = set(df_transactions['brand_name'].unique())
    brands_in_mapping = set(df_mapping['brand_name'].unique())

    unmapped_brands = brands_in_db - brands_in_mapping

    assert not unmapped_brands, (
        f"Coverage Fail: The following {len(unmapped_brands)} brands from the "
        f"database are not in the mapping file: {unmapped_brands}"
    )

    # 4. Perform Revenue Reconciliation Check
    # Merge transactions with their section mapping
    df_merged = pd.merge(
        df_transactions,
        df_mapping[['brand_name', 'section']],
        on='brand_name',
        how='left'
    )

    # Calculate total revenue from the sum of sections
    section_revenue_total = df_merged['nmv'].sum()

    # Get the definitive total revenue directly from the database source
    db_revenue_total = df_transactions['nmv'].sum()

    # Use a small tolerance for floating point comparisons
    assert abs(section_revenue_total - db_revenue_total) < 0.01, (
        f"Revenue Mismatch: Sum of section revenue ({section_revenue_total:.2f}) "
        f"does not equal total DB revenue ({db_revenue_total:.2f})."
    )

