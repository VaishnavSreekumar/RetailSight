# Section Revenue Reconciliation Report

This document verifies that the brand-to-section mapping can fully account for all financial data in the Brigade transaction dataset.

## 1. Brand Coverage Report

The reconciliation script compared the 22 distinct brands in the `brigade_transactions` table against the `brand_to_section_mapping.json` file.

| Metric | Value |
| :--- | :--- |
| Total Brands in Dataset | 22 |
| Mapped Brands | 22 |
| Unmapped Brands | **0** |
| **Coverage Percentage** | **100.00%** |

**Conclusion**: Every brand present in the transaction data has been successfully mapped to a physical store section.

### Informational Mappings

The following brands are defined in the mapping file for future use but do not have corresponding transactions in the current dataset. This is expected and does not affect revenue reconciliation.
* Aqualogica
* Minimalist
* The Face Shop

## 2. Revenue by Section

The following table shows the aggregated financial metrics for each defined store section, derived directly from the Brigade dataset.

| Section | Revenue (NMV) | Revenue (GMV) | Transaction Count | Unique Brands | Avg. Basket Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CENTRAL_DISPLAY | 2,532.65 | 2,960.00 | 8 | 3 | 316.58 |
| MAKEUP_WALL | 21,518.49 | 28,357.00 | 60 | 8 | 358.64 |
| PMU_SECTION | 742.10 | 794.00 | 4 | 2 | 185.53 |
| SKINCARE_WALL | 10,038.50 | 12,809.00 | 29 | 9 | 346.16 |

## 3. Final Revenue Reconciliation

A final check was performed to ensure that the sum of revenue across all sections equals the total revenue in the source dataset.

* **Total Revenue Across All Sections (NMV)**: `34,831.74`
* **Total Revenue in `brigade_transactions` Table (NMV)**: `34,831.74`

**Result**: ✅ **SUCCESS**. The numbers match exactly.

## 4. Confidence Distribution

This table shows the distribution of mapping confidence levels for the brands included in this analysis.

| Confidence Level | Brand Count |
| :--- | :--- |
| HIGH | 8 |
| MEDIUM | 14 |
| LOW | 0 |

This confirms that while all brands are mapped, a significant portion are based on logical assumptions rather than direct visibility on the floor plan.
