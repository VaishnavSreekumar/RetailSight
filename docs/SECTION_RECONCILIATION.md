# Section Revenue Reconciliation Report

This document verifies that the brand-to-section mapping can fully account for all financial data in the Brigade transaction dataset.

## 1. Brand Coverage Report

The reconciliation script compared the 20 distinct brands in the `brigade_transactions` table against the `brand_to_section_mapping.json` file.

| Metric | Value |
| :--- | :--- |
| Total Brands in Dataset | 20 |
| Mapped Brands | 20 |
| Unmapped Brands | **0** |
| **Coverage Percentage** | **100.00%** |

**Conclusion**: Every brand present in the transaction data has been successfully mapped to a physical store section.

### Informational Mappings

The following brands are defined in the mapping file for future use but do not have corresponding transactions in the current dataset. This is expected and does not affect revenue reconciliation.
*   Aqualogica
*   Good Vibes
*   Minimalist
*   The Face Shop

## 2. Revenue by Section

The following table shows the aggregated financial metrics for each defined store section, derived directly from the Brigade dataset.

| Section | Revenue (NMV) | Revenue (GMV) | Transaction Count | Unique Brands | Avg. Basket Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CENTRAL_DISPLAY | 25,842.50 | 27,350.00 | 20 | 5 | 1,292.13 |
| MAKEUP_WALL | 78,111.35 | 82,644.00 | 60 | 11 | 1,301.86 |
| PMU_SECTION | 15,200.00 | 16,000.00 | 10 | 3 | 1,520.00 |
| SKINCARE_WALL | 11,652.50 | 12,250.00 | 11 | 1 | 1,059.32 |

## 3. Final Revenue Reconciliation

A final check was performed to ensure that the sum of revenue across all sections equals the total revenue in the source dataset.

*   **Total Revenue Across All Sections (NMV)**: `130,806.35`
*   **Total Revenue in `brigade_transactions` Table (NMV)**: `130,806.35`

**Result**: ✅ **SUCCESS**. The numbers match exactly.

## 4. Confidence Distribution

This table shows the distribution of mapping confidence levels for the brands included in this analysis.

| Confidence Level | Brand Count |
| :--- | :--- |
| HIGH | 8 |
| MEDIUM | 12 |
| LOW | 0 |

This confirms that while all brands are mapped, a significant portion are based on logical assumptions rather than direct visibility on the floor plan.
