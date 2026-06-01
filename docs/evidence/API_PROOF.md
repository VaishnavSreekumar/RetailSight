# API Proof of Concept

This document serves as verification evidence of the API endpoints, showing actual responses fetched from a clean-clone Docker deployment.

Generated from clean-clone Docker deployment validation on 2026-06-01.

---

## 1. Metrics Endpoint
`GET /metrics`

```json
{
  "store_id": "STORE_VAL_01",
  "visitors": 74,
  "engaged_visitors": 49,
  "billing_queue_visitors": 0,
  "purchases": 0,
  "conversion_rate": 0.0,
  "avg_session_dwell_ms": 6140.4,
  "avg_journey_length": 0.66,
  "avg_zones_visited": 0.66,
  "opportunity_zones": [],
  "generated_at": "2026-06-01T08:13:13.488742+00:00"
}
```

---

## 2. Executive Dashboard Endpoint
`GET /executive-dashboard`

```json
{
  "revenue": {
    "nmv": 34831.73999999999,
    "gmv": 44920.0,
    "abv": 1451.3224999999995
  },
  "sections": [
    {
      "section_name": "MAKEUP_WALL",
      "nmv": 21518.490000000005,
      "gmv": 28357.0,
      "transaction_count": 19,
      "abv": 1132.5521052631582
    },
    {
      "section_name": "SKINCARE_WALL",
      "nmv": 10038.5,
      "gmv": 12809.0,
      "transaction_count": 12,
      "abv": 836.5416666666666
    },
    {
      "section_name": "CENTRAL_DISPLAY",
      "nmv": 2532.65,
      "gmv": 2960.0,
      "transaction_count": 5,
      "abv": 506.53000000000003
    },
    {
      "section_name": "PMU_SECTION",
      "nmv": 742.1,
      "gmv": 794.0,
      "transaction_count": 3,
      "abv": 247.36666666666667
    }
  ],
  "top_brands": [
    {
      "brand_name": "Faces Canada",
      "nmv": 15697.210000000001
    },
    {
      "brand_name": "NY Bae",
      "nmv": 2342.6
    },
    {
      "brand_name": "COSRX",
      "nmv": 2070.0
    },
    {
      "brand_name": "Maybelline",
      "nmv": 1834.29
    },
    {
      "brand_name": "Round Lab",
      "nmv": 1799.0
    }
  ],
  "top_salespeople": [
    {
      "name": "Zufishan Khazra",
      "sales_value": 16583.379999999997,
      "units_sold": 53
    },
    {
      "name": "kasthuri v",
      "sales_value": 6541.95,
      "units_sold": 20
    },
    {
      "name": "Shashikala .",
      "sales_value": 4631.7,
      "units_sold": 12
    },
    {
      "name": "Priya v",
      "sales_value": 3665.75,
      "units_sold": 16
    },
    {
      "name": "Naziya Begum",
      "sales_value": 3408.96,
      "units_sold": 9
    }
  ],
  "customer_behavior": null,
  "layout_insights": {
    "highest_revenue_section": "MAKEUP_WALL",
    "lowest_revenue_section": "PMU_SECTION",
    "highest_abv_section": "MAKEUP_WALL"
  },
  "behavior_insights": {
    "best_converting_section": "SKINCARE_WALL",
    "worst_converting_section": "SKINCARE_WALL",
    "highest_dwell_section": "SKINCARE_WALL"
  }
}
```

---

## 3. Shopper Behavior Endpoint
`GET /shopper-behavior`

```json
{
  "sections": [
    {
      "section_name": "CENTRAL_DISPLAY",
      "visitor_count": 0,
      "avg_dwell_seconds": 0.0,
      "purchase_count": 5,
      "conversion_rate": 0.0
    },
    {
      "section_name": "MAKEUP_WALL",
      "visitor_count": 0,
      "avg_dwell_seconds": 0.0,
      "purchase_count": 19,
      "conversion_rate": 0.0
    },
    {
      "section_name": "SKINCARE_WALL",
      "visitor_count": 49,
      "avg_dwell_seconds": 7.68,
      "purchase_count": 12,
      "conversion_rate": 0.24489795918367346
    },
    {
      "section_name": "PMU_SECTION",
      "visitor_count": 0,
      "avg_dwell_seconds": 0.0,
      "purchase_count": 3,
      "conversion_rate": 0.0
    }
  ],
  "opportunity_zones": [],
  "checkout_intelligence": {
    "queue_entries": 0,
    "completed_purchases": 24,
    "abandonment_rate": 0.0,
    "estimated_lost_revenue": 0.0
  }
}
```
