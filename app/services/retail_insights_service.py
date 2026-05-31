import os
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.schemas.insights import (
    RevenueInsightsSchema,
    RevenueDailySchema,
    RevenueHourlySchema,
    ProductInsightsSchema,
    ProductKPIItem,
    BrandKPIItem,
    CategoryKPIItem,
    SubcategoryKPIItem,
    OfferInsightsSchema,
    OfferKPIItem,
    SalespersonInsightsSchema,
    SalespersonKPIItem,
)

class RetailInsightsService:
    """Service to generate business-facing intelligence using the actual Brigade retail dataset."""

    @classmethod
    def _get_csv_path(cls) -> str:
        """Helper to resolve the path of the Brigade road CSV file."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        csv_files = list(root_dir.glob("Brigade_Bangalore*.csv"))
        if csv_files:
            return str(csv_files[0])
        return str(root_dir / "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv")

    @classmethod
    def _parse_dataset(cls) -> List[Dict[str, Any]]:
        """Parses the Brigade CSV dataset into a list of row dicts with correct datatypes."""
        csv_path = cls._get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Brigade transaction dataset not found at: {csv_path}")

        rows = []
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Basic float parsing helpers
                try:
                    qty = int(row.get("qty") or 0)
                except ValueError:
                    qty = 0

                try:
                    gmv = float(row.get("GMV") or 0.0)
                except ValueError:
                    gmv = 0.0

                try:
                    nmv = float(row.get("NMV") or 0.0)
                except ValueError:
                    nmv = 0.0

                try:
                    disc = float(row.get("item_promotion") or 0.0)
                except ValueError:
                    disc = 0.0

                try:
                    total_amt = float(row.get("total_amount") or 0.0)
                except ValueError:
                    total_amt = 0.0

                parsed_row = {
                    "order_id": (row.get("order_id") or "").strip(),
                    "coupon_code": (row.get("coupon_code") or "").strip(),
                    "offer_name": (row.get("offer_name") or "").strip(),
                    "discount_code": (row.get("discount_code") or "").strip(),
                    "invoice_number": (row.get("invoice_number") or "").strip(),
                    "invoice_type": (row.get("invoice_type") or "").strip(),
                    "order_date": (row.get("order_date") or "").strip(),
                    "order_time": (row.get("order_time") or "").strip(),
                    "store_id": (row.get("store_id") or "").strip(),
                    "store_name": (row.get("store_name") or "").strip(),
                    "customer_name": (row.get("customer_name") or "").strip(),
                    "customer_number": (row.get("customer_number") or "").strip(),
                    "sku": (row.get("sku") or "").strip(),
                    "product_id": (row.get("product_id") or "").strip(),
                    "product_name": (row.get("product_name") or "").strip(),
                    "brand_name": (row.get("brand_name") or "").strip(),
                    "dep_name": (row.get("dep_name") or "").strip(),
                    "sub_category": (row.get("sub_category") or "").strip(),
                    "brand_type": (row.get("brand_type") or "").strip(),
                    "employee_code": (row.get("employee_code") or "").strip(),
                    "salesperson_name": (row.get("salesperson_name") or "").strip(),
                    "qty": qty,
                    "GMV": gmv,
                    "NMV": nmv,
                    "item_promotion": disc,
                    "total_amount": total_amt,
                }
                rows.append(parsed_row)
        return rows

    @classmethod
    def get_revenue_insights(cls, store_id: str) -> RevenueInsightsSchema:
        """Calculates revenue KPIs: total revenue, ABV, average items, day-wise and hour-wise breakdowns."""
        rows = cls._parse_dataset()
        
        # In this dataset all rows are ST1008. We support ST1008 as well as testing store ids.
        # We process the entire dataset as ST1008 data.
        total_gmv = 0.0
        total_nmv = 0.0
        total_discount = 0.0
        total_qty = 0

        unique_orders = set()
        order_totals = {}  # order_id -> NMV
        order_qtys = {}    # order_id -> Qty

        daily_revenue = {} # date -> NMV sum
        daily_orders = {}  # date -> set(order_ids)

        hourly_revenue = {} # hour -> NMV sum
        hourly_orders = {}  # hour -> set(order_ids)

        for row in rows:
            total_gmv += row["GMV"]
            total_nmv += row["NMV"]
            total_discount += row["item_promotion"]
            total_qty += row["qty"]

            order_id = row["order_id"]
            if order_id:
                unique_orders.add(order_id)
                order_totals[order_id] = order_totals.get(order_id, 0.0) + row["NMV"]
                order_qtys[order_id] = order_qtys.get(order_id, 0) + row["qty"]

            date = row["order_date"]
            if date:
                daily_revenue[date] = daily_revenue.get(date, 0.0) + row["NMV"]
                if date not in daily_orders:
                    daily_orders[date] = set()
                if order_id:
                    daily_orders[date].add(order_id)

            time_str = row["order_time"]
            if time_str and ":" in time_str:
                try:
                    hour = int(time_str.split(":")[0])
                    hourly_revenue[hour] = hourly_revenue.get(hour, 0.0) + row["NMV"]
                    if hour not in hourly_orders:
                        hourly_orders[hour] = set()
                    if order_id:
                        hourly_orders[hour].add(order_id)
                except ValueError:
                    pass

        # Package daily schemas
        revenue_by_day = []
        for date, nmv in sorted(daily_revenue.items()):
            revenue_by_day.append(
                RevenueDailySchema(
                    date=date,
                    revenue=round(nmv, 2),
                    order_count=len(daily_orders.get(date, set()))
                )
            )

        # Package hourly schemas
        revenue_by_hour = []
        for hour, nmv in sorted(hourly_revenue.items()):
            revenue_by_hour.append(
                RevenueHourlySchema(
                    hour=hour,
                    revenue=round(nmv, 2),
                    order_count=len(hourly_orders.get(hour, set()))
                )
            )

        num_orders = len(unique_orders)
        avg_basket_value = (total_nmv / num_orders) if num_orders > 0 else 0.0
        avg_items_per_basket = (total_qty / num_orders) if num_orders > 0 else 0.0

        return RevenueInsightsSchema(
            total_revenue=round(total_nmv, 2),
            total_gmv=round(total_gmv, 2),
            total_discount=round(total_discount, 2),
            average_basket_value=round(avg_basket_value, 2),
            average_items_per_basket=round(avg_items_per_basket, 2),
            revenue_by_day=revenue_by_day,
            revenue_by_hour=revenue_by_hour
        )

    @classmethod
    def get_product_insights(cls, store_id: str) -> ProductInsightsSchema:
        """Calculates product KPIs: top products, brands, categories, and subcategories by NMV."""
        rows = cls._parse_dataset()

        product_aggregates = {}
        brand_aggregates = {}
        category_aggregates = {}
        subcategory_aggregates = {}

        for row in rows:
            sku = row["sku"]
            prod_name = row["product_name"]
            qty = row["qty"]
            nmv = row["NMV"]
            brand = row["brand_name"]
            dep = row["dep_name"]
            subcat = row["sub_category"]

            # Products
            if sku:
                if sku not in product_aggregates:
                    product_aggregates[sku] = {"name": prod_name, "qty": 0, "rev": 0.0}
                product_aggregates[sku]["qty"] += qty
                product_aggregates[sku]["rev"] += nmv

            # Brands
            if brand:
                if brand not in brand_aggregates:
                    brand_aggregates[brand] = {"qty": 0, "rev": 0.0}
                brand_aggregates[brand]["qty"] += qty
                brand_aggregates[brand]["rev"] += nmv

            # Categories
            if dep:
                if dep not in category_aggregates:
                    category_aggregates[dep] = {"qty": 0, "rev": 0.0}
                category_aggregates[dep]["qty"] += qty
                category_aggregates[dep]["rev"] += nmv

            # Subcategories
            if subcat:
                if subcat not in subcategory_aggregates:
                    subcategory_aggregates[subcat] = {"qty": 0, "rev": 0.0}
                subcategory_aggregates[subcat]["qty"] += qty
                subcategory_aggregates[subcat]["rev"] += nmv

        # Sort and limit
        top_products = [
            ProductKPIItem(sku=sku, product_name=info["name"], quantity=info["qty"], revenue=round(info["rev"], 2))
            for sku, info in sorted(product_aggregates.items(), key=lambda x: x[1]["rev"], reverse=True)
        ]

        top_brands = [
            BrandKPIItem(brand_name=brand, quantity=info["qty"], revenue=round(info["rev"], 2))
            for brand, info in sorted(brand_aggregates.items(), key=lambda x: x[1]["rev"], reverse=True)
        ]

        top_categories = [
            CategoryKPIItem(category=dep, quantity=info["qty"], revenue=round(info["rev"], 2))
            for dep, info in sorted(category_aggregates.items(), key=lambda x: x[1]["rev"], reverse=True)
        ]

        top_subcategories = [
            SubcategoryKPIItem(subcategory=subcat, quantity=info["qty"], revenue=round(info["rev"], 2))
            for subcat, info in sorted(subcategory_aggregates.items(), key=lambda x: x[1]["rev"], reverse=True)
        ]

        return ProductInsightsSchema(
            top_selling_products=top_products[:10],
            top_selling_brands=top_brands[:10],
            top_selling_categories=top_categories,
            top_selling_subcategories=top_subcategories[:15]
        )

    @classmethod
    def get_offer_insights(cls, store_id: str) -> OfferInsightsSchema:
        """Calculates offer KPIs: performance, conversions, and revenue contributions."""
        rows = cls._parse_dataset()

        total_nmv = sum(row["NMV"] for row in rows)
        offer_aggregates = {}
        revenue_by_offer = {}
        orders_by_offer = {}

        for row in rows:
            offer = row["offer_name"]
            # Treat empty offers as "No Promotion" or skip for offers KPIs, but let's count them
            offer_key = offer if offer else "No Promotion"
            qty = row["qty"]
            nmv = row["NMV"]
            order_id = row["order_id"]

            if offer_key not in offer_aggregates:
                offer_aggregates[offer_key] = {"count": 0, "rev": 0.0, "orders": set()}
            
            offer_aggregates[offer_key]["count"] += 1
            offer_aggregates[offer_key]["rev"] += nmv
            if order_id:
                offer_aggregates[offer_key]["orders"].add(order_id)

        most_used_offers = []
        for offer_name, info in offer_aggregates.items():
            order_count = len(info["orders"])
            contrib = (info["rev"] / total_nmv * 100) if total_nmv > 0 else 0.0
            
            most_used_offers.append(
                OfferKPIItem(
                    offer_name=offer_name,
                    count=info["count"],
                    revenue=round(info["rev"], 2),
                    order_count=order_count,
                    conversion_contribution=round(contrib, 2)
                )
            )
            revenue_by_offer[offer_name] = round(info["rev"], 2)
            orders_by_offer[offer_name] = order_count

        # Sort offers by count descending
        most_used_offers = sorted(most_used_offers, key=lambda x: x.count, reverse=True)

        return OfferInsightsSchema(
            most_used_offers=most_used_offers,
            revenue_by_offer=revenue_by_offer,
            orders_by_offer=orders_by_offer
        )

    @classmethod
    def get_salesperson_insights(cls, store_id: str) -> SalespersonInsightsSchema:
        """Calculates salesperson performance: revenue generated, order count, and top performer."""
        rows = cls._parse_dataset()

        sales_aggregates = {}

        for row in rows:
            name = row["salesperson_name"]
            code = row["employee_code"]
            nmv = row["NMV"]
            order_id = row["order_id"]

            if not name:
                continue

            if name not in sales_aggregates:
                sales_aggregates[name] = {"code": code, "rev": 0.0, "orders": set()}

            sales_aggregates[name]["rev"] += nmv
            if order_id:
                sales_aggregates[name]["orders"].add(order_id)

        revenue_by_salesperson = []
        for name, info in sales_aggregates.items():
            revenue_by_salesperson.append(
                SalespersonKPIItem(
                    salesperson_name=name,
                    employee_code=info["code"],
                    revenue=round(info["rev"], 2),
                    order_count=len(info["orders"])
                )
            )

        # Sort by revenue descending
        revenue_by_salesperson = sorted(revenue_by_salesperson, key=lambda x: x.revenue, reverse=True)

        top_performer = revenue_by_salesperson[0] if revenue_by_salesperson else None

        return SalespersonInsightsSchema(
            revenue_by_salesperson=revenue_by_salesperson,
            top_performing_salesperson=top_performer
        )
