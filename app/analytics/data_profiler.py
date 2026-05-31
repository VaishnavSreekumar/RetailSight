import os
import csv
from pathlib import Path
from typing import Dict, Any, List

class DataProfiler:
    """Utility class to profile the Brigade road retail transaction dataset using pure Python."""

    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Resolve to root-level CSV
            root_dir = Path(__file__).resolve().parent.parent.parent
            # Find any CSV starting with Brigade_Bangalore in root
            csv_files = list(root_dir.glob("Brigade_Bangalore*.csv"))
            if csv_files:
                self.csv_path = str(csv_files[0])
            else:
                self.csv_path = str(root_dir / "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv")
        else:
            self.csv_path = csv_path

    def profile_dataset(self) -> Dict[str, Any]:
        """Performs full dataset profiling and returns aggregated metrics."""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Brigade transaction dataset not found at: {self.csv_path}")

        total_rows = 0
        columns_nulls = {}
        unique_orders = set()
        unique_customers = set()
        unique_products = set()
        unique_brands = set()
        unique_departments = set()
        unique_subcategories = set()
        unique_salespeople = set()
        unique_offers = set()

        total_gmv = 0.0
        total_nmv = 0.0
        total_qty = 0
        total_discount = 0.0

        category_stats = {}
        brand_stats = {}
        offer_stats = {}
        salesperson_stats = {}
        hourly_stats = {}
        daily_stats = {}

        # First pass to read all columns
        with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames if reader.fieldnames else []
            for col in fieldnames:
                columns_nulls[col] = 0

            for row in reader:
                total_rows += 1
                
                # Check for nulls/empty
                for col in fieldnames:
                    val = row.get(col, "").strip()
                    if not val or val.lower() == "nan" or val.lower() == "null":
                        columns_nulls[col] += 1

                # Unique sets
                order_id = row.get("order_id", "").strip()
                if order_id:
                    unique_orders.add(order_id)
                
                cust_num = row.get("customer_number", "").strip()
                if cust_num:
                    unique_customers.add(cust_num)

                sku = row.get("sku", "").strip()
                if sku:
                    unique_products.add(sku)

                brand = row.get("brand_name", "").strip()
                if brand:
                    unique_brands.add(brand)

                dep = row.get("dep_name", "").strip()
                if dep:
                    unique_departments.add(dep)

                subcat = row.get("sub_category", "").strip()
                if subcat:
                    unique_subcategories.add(subcat)

                sales_name = row.get("salesperson_name", "").strip()
                if sales_name:
                    unique_salespeople.add(sales_name)

                offer = row.get("offer_name", "").strip()
                if offer:
                    unique_offers.add(offer)

                # Quantities and amounts
                try:
                    qty = int(row.get("qty") or 0)
                except ValueError:
                    qty = 0
                total_qty += qty

                try:
                    gmv = float(row.get("GMV") or 0.0)
                except ValueError:
                    gmv = 0.0
                total_gmv += gmv

                try:
                    nmv = float(row.get("NMV") or 0.0)
                except ValueError:
                    nmv = 0.0
                total_nmv += nmv

                try:
                    disc = float(row.get("item_promotion") or 0.0)
                except ValueError:
                    disc = 0.0
                total_discount += disc

                # Department stats
                if dep:
                    if dep not in category_stats:
                        category_stats[dep] = {"count": 0, "gmv": 0.0, "nmv": 0.0, "qty": 0}
                    category_stats[dep]["count"] += 1
                    category_stats[dep]["gmv"] += gmv
                    category_stats[dep]["nmv"] += nmv
                    category_stats[dep]["qty"] += qty

                # Brand stats
                if brand:
                    if brand not in brand_stats:
                        brand_stats[brand] = {"count": 0, "gmv": 0.0, "nmv": 0.0, "qty": 0}
                    brand_stats[brand]["count"] += 1
                    brand_stats[brand]["gmv"] += gmv
                    brand_stats[brand]["nmv"] += nmv
                    brand_stats[brand]["qty"] += qty

                # Offer stats
                if offer:
                    if offer not in offer_stats:
                        offer_stats[offer] = {"count": 0, "gmv": 0.0, "nmv": 0.0, "qty": 0}
                    offer_stats[offer]["count"] += 1
                    offer_stats[offer]["gmv"] += gmv
                    offer_stats[offer]["nmv"] += nmv
                    offer_stats[offer]["qty"] += qty

                # Salesperson stats
                if sales_name:
                    if sales_name not in salesperson_stats:
                        salesperson_stats[sales_name] = {"count": 0, "gmv": 0.0, "nmv": 0.0, "qty": 0}
                    salesperson_stats[sales_name]["count"] += 1
                    salesperson_stats[sales_name]["gmv"] += gmv
                    salesperson_stats[sales_name]["nmv"] += nmv
                    salesperson_stats[sales_name]["qty"] += qty

                # Temporal stats
                order_time = row.get("order_time", "").strip()
                if order_time and ":" in order_time:
                    hour = order_time.split(":")[0]
                    try:
                        hour_val = int(hour)
                        if hour_val not in hourly_stats:
                            hourly_stats[hour_val] = {"count": 0, "nmv": 0.0}
                        hourly_stats[hour_val]["count"] += 1
                        hourly_stats[hour_val]["nmv"] += nmv
                    except ValueError:
                        pass

                order_date = row.get("order_date", "").strip()
                if order_date:
                    if order_date not in daily_stats:
                        daily_stats[order_date] = {"count": 0, "nmv": 0.0}
                    daily_stats[order_date]["count"] += 1
                    daily_stats[order_date]["nmv"] += nmv

        # Null percentages
        null_analysis = {}
        for col, count in columns_nulls.items():
            pct = (count / total_rows * 100) if total_rows > 0 else 0
            null_analysis[col] = {"count": count, "percentage": round(pct, 2)}

        # Sorting lists for return/display
        top_categories = sorted(category_stats.items(), key=lambda x: x[1]["nmv"], reverse=True)
        top_brands = sorted(brand_stats.items(), key=lambda x: x[1]["nmv"], reverse=True)
        top_offers = sorted(offer_stats.items(), key=lambda x: x[1]["nmv"], reverse=True)
        top_salespeople = sorted(salesperson_stats.items(), key=lambda x: x[1]["nmv"], reverse=True)

        avg_basket_value = (total_nmv / len(unique_orders)) if unique_orders else 0.0
        avg_items_per_basket = (total_qty / len(unique_orders)) if unique_orders else 0.0

        return {
            "dataset_summary": {
                "total_rows": total_rows,
                "unique_orders": len(unique_orders),
                "unique_customers": len(unique_customers),
                "unique_products": len(unique_products),
                "unique_brands": len(unique_brands),
                "unique_departments": len(unique_departments),
                "unique_subcategories": len(unique_subcategories),
                "unique_salespeople": len(unique_salespeople),
                "unique_offers": len(unique_offers),
            },
            "revenue_summary": {
                "total_gmv": round(total_gmv, 2),
                "total_nmv": round(total_nmv, 2),
                "total_discount": round(total_discount, 2),
                "total_qty": total_qty,
                "avg_basket_value": round(avg_basket_value, 2),
                "avg_items_per_basket": round(avg_items_per_basket, 2),
            },
            "null_analysis": null_analysis,
            "category_distribution": top_categories,
            "brand_distribution": top_brands,
            "offer_distribution": top_offers,
            "salesperson_distribution": top_salespeople,
            "hourly_distribution": sorted(hourly_stats.items()),
            "daily_distribution": sorted(daily_stats.items()),
        }

if __name__ == "__main__":
    import json
    profiler = DataProfiler()
    try:
        results = profiler.profile_dataset()
        print("=== DATASET PROFILE SUMMARY ===")
        print(json.dumps(results["dataset_summary"], indent=2))
        print("\n=== REVENUE SUMMARY ===")
        print(json.dumps(results["revenue_summary"], indent=2))
        print("\n=== TOP 5 CATEGORIES BY NMV ===")
        for name, data in results["category_distribution"][:5]:
            print(f"  {name}: NMV = {data['nmv']:.2f}, Count = {data['count']}, Qty = {data['qty']}")
        print("\n=== TOP 5 BRANDS BY NMV ===")
        for name, data in results["brand_distribution"][:5]:
            print(f"  {name}: NMV = {data['nmv']:.2f}, Count = {data['count']}")
        print("\n=== TOP 5 OFFERS BY NMV ===")
        for name, data in results["offer_distribution"][:5]:
            print(f"  {name}: NMV = {data['nmv']:.2f}, Count = {data['count']}")
        print("\n=== TOP 5 SALESPEOPLE BY NMV ===")
        for name, data in results["salesperson_distribution"][:5]:
            print(f"  {name}: NMV = {data['nmv']:.2f}, Count = {data['count']}")
    except Exception as e:
        print(f"Error during profiling: {e}")
