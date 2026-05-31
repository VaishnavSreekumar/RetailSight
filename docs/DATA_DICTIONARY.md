# Brigade Road Retail Dataset - Data Dictionary

This document profiles and documents the real transaction dataset for the **Brigade Road (Bangalore)** store location (`ST1008`). It provides the column schemas, data types, missing/null value analysis, and critical distributions used by the business intelligence engine.

---

## 1. Dataset Profiling Summary
Based on the direct automated profiling of `Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv`:

- **Total Transaction Rows (Items)**: 101
- **Unique Orders (Baskets)**: 24
- **Unique Customers**: 21
- **Unique Products (SKUs)**: 83
- **Unique Brands**: 22
- **Unique Categories (Departments)**: 6
- **Unique Subcategories**: 41
- **Unique Salespeople**: 5
- **Unique Offers Applied**: 9

### Financial Baseline
- **Total Gross Merchandise Value (GMV)**: ₹44,920.00
- **Total Net Merchandise Value (NMV)**: ₹34,831.74
- **Total Applied Discounts/Promotions**: ₹10,088.26
- **Total Items Sold**: 117 units
- **Average Basket Value (NMV per Order)**: ₹1,451.32
- **Average Items Per Basket (Qty per Order)**: 4.88 items

---

## 2. Data Schema & Dictionary

The Brigade transaction dataset contains 39 columns tracking transaction attributes, product classification, customer identification, promotional structures, tax parameters, and employee metadata.

| Column Name | Data Type | Missing Values (Count / %) | Key Category | Business Description & Sample Value |
| :--- | :--- | :--- | :--- | :--- |
| **order_id** | String | 0 (0.00%) | Customer / Order | Unique identifier for the checkout event. e.g., `104363838` |
| **coupon_code** | String | 96 (95.05%) | Offer / Promo | Customer-applied coupon code. e.g., `MAR2620` |
| **offer_name** | String | 24 (23.76%) | Offer / Promo | In-store campaign or promotion applied. e.g., `Buy 2 Get 1 on PB` |
| **discount_code** | String | 96 (95.05%) | Offer / Promo | System code for specific discounts. e.g., `MAR2620` |
| **invoice_number** | String | 0 (0.00%) | Customer / Order | Legal invoice sequence generated. e.g., `ML0426KAP0001358` |
| **invoice_type** | String | 0 (0.00%) | Customer / Order | Type of transaction. Always `sales` for this dataset. |
| **order_date** | String | 0 (0.00%) | Temporal | Date of purchase (DD-MM-YYYY). e.g., `10-04-2026` |
| **order_time** | String | 0 (0.00%) | Temporal | Timestamp of transaction (HH:MM:SS). e.g., `16:55:36` |
| **return_id** | String | 101 (100.00%) | Customer / Order | Refund/return linkage, fully null. |
| **store_id** | String | 0 (0.00%) | Location | Store ID mapping to store catalog. Always `ST1008`. |
| **store_name** | String | 0 (0.00%) | Location | Descriptive store name. Always `Brigade_Bangalore`. |
| **city** | String | 0 (0.00%) | Location | City location of store. Always `Bangalore`. |
| **customer_name** | String | 0 (0.00%) | Customer / Order | Name of registered customer. e.g., `sagar`, `Guest ` |
| **customer_number**| String | 0 (0.00%) | Customer / Order | Primary key for customer profile. e.g., `9986216644` |
| **sku** | String | 0 (0.00%) | Product Hierarchy | Stock Keeping Unit code. e.g., `PPLBDD8904362534994NM2` |
| **product_id** | String | 0 (0.00%) | Product Hierarchy | Internal database item ID. e.g., `402813` |
| **ean** | String | 0 (0.00%) | Product Hierarchy | International Article Number. e.g., `8.90436E+12` |
| **product_name** | String | 0 (0.00%) | Product Hierarchy | Retail description of SKU. e.g., `Good Vibes Sheet Mask` |
| **brand_name** | String | 0 (0.00%) | Product Hierarchy | Label/Manufacturer brand. e.g., `Faces Canada`, `DERMDOC` |
| **dep_name** | String | 0 (0.00%) | Product Hierarchy | Root department/category. e.g., `makeup`, `skin`, `hair` |
| **sub_category** | String | 0 (0.00%) | Product Hierarchy | Granular sub-department. e.g., `Lipstick`, `Foundation` |
| **brand_type** | String | 0 (0.00%) | Product Hierarchy | Brand origin type. e.g., `PB` (Private Brand), `Exclusive` |
| **tax** | Numeric | 0 (0.00%) | Financial / Tax | Standard tax rate in percentage. e.g., `18` (18% GST) |
| **hsn_code** | String | 0 (0.00%) | Financial / Tax | Harmonized System Nomenclature for taxation. e.g., `33049990` |
| **salesperson_id** | String | 0 (0.00%) | Employee | Numerical ID of sales employee. e.g., `1178`, `971` |
| **employee_code** | String | 0 (0.00%) | Employee | Alphanumeric employee registry code. e.g., `CL2063`, `CL2727` |
| **salesperson_name**| String | 0 (0.00%) | Employee | Professional name of salesperson. e.g., `Zufishan Khazra` |
| **qty** | Integer | 0 (0.00%) | Financial / Qty | Physical count of items purchased. e.g., `1`, `2` |
| **GMV** | Numeric | 0 (0.00%) | Financial / Rev | Gross merchandise value prior to discounts. e.g., `400.0` |
| **NMV** | Numeric | 0 (0.00%) | Financial / Rev | Net merchandise value after promo/coupon. e.g., `274.36` |
| **coupon_amount** | Numeric | 2 (1.98%) | Financial / Rev | Deducted amount from coupon codes. e.g., `0.2` |
| **item_promotion** | Numeric | 2 (1.98%) | Financial / Rev | Promotion discount value. e.g., `125.64` |
| **amt_without_gwp** | Numeric | 2 (1.98%) | Financial / Rev | Total transaction net amount minus gift items. |
| **total_amount** | Numeric | 2 (1.98%) | Financial / Rev | Net legal item total payable. e.g., `274.36` |
| **pb_eb_sale** | String | 101 (100.00%) | Offer / Promo | Special internal sales categorization, fully null. |
| **week_assigned** | String | 101 (100.00%) | Temporal | Week sequence number, fully null. |
| **tax_m** | Numeric | 2 (1.98%) | Financial / Tax | Tax multiplier used. e.g., `1.18` (representing 1.18x) |
| **taxable_amt** | Numeric | 2 (1.98%) | Financial / Tax | Net amount subject to tax calculations. e.g., `232.51` |
| **tax_amt** | Numeric | 2 (1.98%) | Financial / Tax | Total calculated tax. e.g., `41.85` |

---

## 3. Product & Brand Distribution

### Category Breakdown
The catalog spans 6 physical store categories:
1. **makeup**: ₹21,939.09 NMV (54 transactions, 55 items) — *Primary Revenue Driver*
2. **skin**: ₹9,408.28 NMV (27 transactions, 42 items)
3. **hair**: ₹1,957.15 NMV (6 transactions, 6 items)
4. **personal-care**: ₹763.80 NMV (4 transactions, 4 items)
5. **bath-and-body**: ₹514.42 NMV (9 transactions, 9 items)
6. **fragrance**: ₹249.00 NMV (1 transaction, 1 item)

### Brand Performance
Top brands contributing to store performance:
- **Faces Canada**: ₹15,697.21 (32 transaction lines) — *Unrivaled Anchor Brand*
- **NY Bae**: ₹2,342.60 (10 transaction lines)
- **COSRX**: ₹2,070.00 (2 transaction lines)
- **Maybelline**: ₹1,834.29 (3 transaction lines)
- **Round Lab**: ₹1,799.00 (1 transaction line)

---

## 4. Salesperson Registry
Five salespeople drive store conversions:
1. **Zufishan Khazra**: ₹16,583.38 NMV (42 lines) — *Highest Performer*
2. **kasthuri v**: ₹6,541.95 NMV (19 lines)
3. **Shashikala .**: ₹4,631.70 NMV (12 lines)
4. **Priya v**: ₹3,665.75 NMV (13 lines)
5. **Naziya Begum**: ₹3,408.96 NMV (8 lines)

---

## 5. Temporal Distributions

The data covers an entire active day on **10-04-2026**. Peak checkout hours represent critical store capacity bottlenecks:
- **12:00 - 13:00**: ₹2,137.64 NMV
- **13:00 - 14:00**: ₹398.00 NMV
- **14:00 - 15:00**: ₹225.00 NMV
- **15:00 - 16:00**: ₹1,624.64 NMV
- **16:00 - 17:00**: ₹3,842.27 NMV — *Pre-evening Peak*
- **17:00 - 18:00**: ₹1,595.73 NMV
- **18:00 - 19:00**: ₹3,874.10 NMV — *Evening Rush 1*
- **19:00 - 20:00**: ₹17,730.26 NMV — *Super Peak Checkout Hour (over 50% of revenue)*
- **20:00 - 21:00**: ₹3,149.00 NMV
- **21:00 - 22:00**: ₹1,255.10 NMV
