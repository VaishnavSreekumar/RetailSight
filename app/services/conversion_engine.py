from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Metric contracts
# ---------------------------------------------------------------------------
# conversion_rate   : percentage, range [0.0, 100.0]  — e.g. 38.46 means 38.46 %
# abandonment_rate  : fraction,   range [0.0, 1.0]    — e.g. 0.33  means 33 %
# All intermediate boolean flags (has_converted, has_joined_billing_queue)
# originate from the visitor_sessions table populated by the CCTV pipeline.
# ---------------------------------------------------------------------------

# Helper to retrieve attributes from either objects or dicts
def _get_field(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class ConversionEngine:
    """Service class responsible for retail conversion analytics and performance auditing."""

    @staticmethod
    def calculate_funnel(sessions: Sequence[Any]) -> dict[str, Any]:
        """Calculates store-wide visitor progression metrics through conversion milestones."""
        sessions = [s for s in sessions if not _get_field(s, "is_staff", False)]
        entries = len(sessions)
        if entries == 0:
            return {
                "entries": 0,
                "engaged_visitors": 0,
                "billing_queue_visitors": 0,
                "purchases": 0,
                "conversion_rate": 0.0,
                "avg_journey_length": 0.0,
            }

        engaged_visitors = 0
        billing_queue_visitors = 0
        purchases = 0
        total_journey_length = 0

        for session in sessions:
            journey_path = _get_field(session, "journey_path") or []
            total_journey_length += len(journey_path)
            
            if len(journey_path) > 0:
                engaged_visitors += 1

            if _get_field(session, "has_joined_billing_queue", False):
                billing_queue_visitors += 1

            if _get_field(session, "has_converted", False):
                purchases += 1

        # Formula: conversion_rate = (purchases / total_entries) * 100
        # Output contract: percentage in range [0.0, 100.0]
        conversion_rate = round((purchases / entries) * 100, 2)
        avg_journey_length = round(total_journey_length / entries, 2)

        return {
            "entries": entries,
            "engaged_visitors": engaged_visitors,
            "billing_queue_visitors": billing_queue_visitors,
            "purchases": purchases,
            "conversion_rate": conversion_rate,
            "avg_journey_length": avg_journey_length,
        }

    @staticmethod
    def calculate_zone_effectiveness(sessions: Sequence[Any]) -> dict[str, dict[str, Any]]:
        """Computes counts, dwell averages, and conversion progression rates for each zone."""
        sessions = [s for s in sessions if not _get_field(s, "is_staff", False)]
        # zone_id -> list of sessions that visited that zone
        zone_visits = {}

        for session in sessions:
            journey_path = _get_field(session, "journey_path") or []
            dwells = _get_field(session, "zone_dwell_times") or {}
            
            # Identify unique zones visited during this session
            visited_zones = set(journey_path).union(dwells.keys())
            
            for zone_id in visited_zones:
                if zone_id not in zone_visits:
                    zone_visits[zone_id] = []
                zone_visits[zone_id].append(session)

        zone_metrics = {}

        for zone_id, visitor_sessions in zone_visits.items():
            visitors_count = len(visitor_sessions)
            total_dwell = 0
            billing_conversions = 0
            sales_conversions = 0

            for session in visitor_sessions:
                dwells = _get_field(session, "zone_dwell_times") or {}
                total_dwell += dwells.get(zone_id, 0)

                if _get_field(session, "has_joined_billing_queue", False):
                    billing_conversions += 1
                if _get_field(session, "has_converted", False):
                    sales_conversions += 1

            avg_dwell = round(total_dwell / visitors_count, 2) if visitors_count > 0 else 0.0
            billing_progression = (
                round((billing_conversions / visitors_count) * 100, 2)
                if visitors_count > 0
                else 0.0
            )
            downstream_conv = (
                round((sales_conversions / visitors_count) * 100, 2)
                if visitors_count > 0
                else 0.0
            )

            zone_metrics[zone_id] = {
                "visitors_count": visitors_count,
                "average_dwell_ms": avg_dwell,
                "billing_progression_rate": billing_progression,
                "downstream_conversion_rate": downstream_conv,
            }

        return zone_metrics

    @classmethod
    def analyze_opportunity_loss(cls, sessions: Sequence[Any]) -> list[dict[str, Any]]:
        """Identifies zones with high dwell times but low billing progression and purchase conversion rates."""
        sessions = [s for s in sessions if not _get_field(s, "is_staff", False)]
        if not sessions:
            return []

        # 1. Compute overall reference metrics
        funnel = cls.calculate_funnel(sessions)
        overall_conversion_rate = funnel["conversion_rate"]
        
        # Overall store billing progression rate
        total_sessions = len(sessions)
        total_billing_queue = sum(
            1 for s in sessions if _get_field(s, "has_joined_billing_queue", False)
        )
        overall_billing_rate = (
            (total_billing_queue / total_sessions) * 100 if total_sessions > 0 else 0.0
        )

        # 2. Compute individual zone metrics
        zone_metrics = cls.calculate_zone_effectiveness(sessions)
        if not zone_metrics:
            return []

        # Calculate store-wide average dwell time across all recorded zones
        total_dwell_average = sum(
            z["average_dwell_ms"] for z in zone_metrics.values()
        ) / len(zone_metrics)

        flagged_zones = []

        # 3. Identify opportunity loss zones
        for zone_id, metrics in zone_metrics.items():
            dwell_ms = metrics["average_dwell_ms"]
            conversion_rate = metrics["downstream_conversion_rate"]
            billing_rate = metrics["billing_progression_rate"]

            # Highlight zones matching all target criteria:
            # - High Average Dwell (above average across all zones)
            # - Low Downstream Conversion (below store average conversion)
            # - Low Billing Queue Progression (below store average billing queue rate)
            if (
                dwell_ms > total_dwell_average
                and conversion_rate < overall_conversion_rate
                and billing_rate < overall_billing_rate
            ):
                flagged_zones.append(
                    {
                        "zone": zone_id,
                        "avg_dwell_ms": dwell_ms,
                        "conversion_rate": conversion_rate,
                        "billing_progression_rate": billing_rate,
                        "severity": "HIGH",
                        "reason": "High dwell but low billing progression",
                    }
                )

        return flagged_zones

    @classmethod
    def calculate_store_metrics(cls, sessions: Sequence[Any]) -> dict[str, Any]:
        """Calculates store-wide metrics for a cohort of visitor sessions."""
        sessions = [s for s in sessions if not _get_field(s, "is_staff", False)]
        if not sessions:
            return {
                "visitors": 0,
                "engaged_visitors": 0,
                "billing_queue_visitors": 0,
                "purchases": 0,
                "conversion_rate": 0.0,
                "avg_session_dwell_ms": 0.0,
                "avg_journey_length": 0.0,
                "avg_zones_visited": 0.0,
                "opportunity_zones": [],
            }

        funnel = cls.calculate_funnel(sessions)

        # Average session dwell time calculation
        dwell_durations = []
        for s in sessions:
            exited = _get_field(s, "exited_at")
            entered = _get_field(s, "entered_at")
            if exited and entered:
                dwell_durations.append((exited - entered).total_seconds() * 1000)
            else:
                dwell_times = _get_field(s, "zone_dwell_times")
                if isinstance(dwell_times, dict) and dwell_times:
                    dwell_durations.append(sum(dwell_times.values()))

        avg_dwell = (
            round(sum(dwell_durations) / len(dwell_durations), 2)
            if dwell_durations
            else 0.0
        )

        # Average unique retail zones visited calculation (excluding ENTRY, EXIT, etc.)
        excluded = {
            "ENTRY", "EXIT", "BILLING", "REENTRY", 
            "BILLING_QUEUE", "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON"
        }

        def is_retail_zone(zone: str) -> bool:
            clean = zone.upper().replace("ZONE_", "").strip()
            return clean not in excluded

        zones_visited_counts = []
        for s in sessions:
            journey_path = _get_field(s, "journey_path") or []
            retail_zones = {z for z in journey_path if is_retail_zone(z)}
            zones_visited_counts.append(len(retail_zones))

        avg_zones = (
            round(sum(zones_visited_counts) / len(sessions), 2)
            if sessions
            else 0.0
        )

        # Opportunity zones analysis
        opp_zones = cls.analyze_opportunity_loss(sessions)

        return {
            "visitors": funnel["entries"],
            "engaged_visitors": funnel["engaged_visitors"],
            "billing_queue_visitors": funnel["billing_queue_visitors"],
            "purchases": funnel["purchases"],
            "conversion_rate": funnel["conversion_rate"],
            "avg_session_dwell_ms": avg_dwell,
            "avg_journey_length": funnel["avg_journey_length"],
            "avg_zones_visited": avg_zones,
            "opportunity_zones": opp_zones,
        }

    @classmethod
    def calculate_funnel_steps(cls, sessions: Sequence[Any]) -> list[dict[str, Any]]:
        """Calculates cohort-based conversion funnel steps with relative preceding-stage rates."""
        sessions = [s for s in sessions if not _get_field(s, "is_staff", False)]
        entries = len(sessions)
        if entries == 0:
            return [
                {"step_name": "Store Entry", "visitor_count": 0, "conversion_rate": 0.0},
                {"step_name": "Browsing Zones", "visitor_count": 0, "conversion_rate": 0.0},
                {"step_name": "Checkout Counter", "visitor_count": 0, "conversion_rate": 0.0},
                {"step_name": "Completed Purchase", "visitor_count": 0, "conversion_rate": 0.0},
            ]

        # Calculate counts
        engaged_visitors = 0
        billing_queue_visitors = 0
        purchases = 0

        for session in sessions:
            journey_path = _get_field(session, "journey_path") or []
            if len(journey_path) > 0:
                engaged_visitors += 1
            if _get_field(session, "has_joined_billing_queue", False):
                billing_queue_visitors += 1
            if _get_field(session, "has_converted", False):
                purchases += 1

        # Calculate rates relative to preceding step
        rate_entry = 100.0
        rate_browsing = round((engaged_visitors / entries) * 100, 2) if entries > 0 else 0.0
        rate_checkout = round((billing_queue_visitors / engaged_visitors) * 100, 2) if engaged_visitors > 0 else 0.0
        rate_purchase = round((purchases / billing_queue_visitors) * 100, 2) if billing_queue_visitors > 0 else 0.0

        return [
            {
                "step_name": "Store Entry",
                "visitor_count": entries,
                "conversion_rate": rate_entry,
            },
            {
                "step_name": "Browsing Zones",
                "visitor_count": engaged_visitors,
                "conversion_rate": rate_browsing,
            },
            {
                "step_name": "Checkout Counter",
                "visitor_count": billing_queue_visitors,
                "conversion_rate": rate_checkout,
            },
            {
                "step_name": "Completed Purchase",
                "visitor_count": purchases,
                "conversion_rate": rate_purchase,
            },
        ]

