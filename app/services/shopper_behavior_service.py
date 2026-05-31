from typing import List, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import aiofiles

from app.models.brigade_transaction import BrigadeTransaction
from app.models.visitor_session import VisitorSession
from app.models.event import Event, EventType
from app.config import BRAND_TO_SECTION_MAPPING_PATH
from app.services.conversion_engine import ConversionEngine
from app.schemas.shopper_behavior import (
    ShopperBehaviorReport, SectionBehaviorMetrics, OpportunityZone,
    CheckoutIntelligence, BehaviorInsights
)

class ShopperBehaviorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_shopper_behavior_report(self, store_id: str) -> ShopperBehaviorReport:
        """
        Generates a report connecting shopper behavior (CCTV) with commerce outcomes.
        """
        # 1. Get Commerce Data (Purchases)
        trans_result = await self.db.execute(select(BrigadeTransaction))
        transactions = trans_result.scalars().all()
        df_trans = pd.DataFrame([t.__dict__ for t in transactions])

        async with aiofiles.open(BRAND_TO_SECTION_MAPPING_PATH, 'r') as f:
            content = await f.read()
            brand_mapping = json.loads(content)
        df_mapping = pd.DataFrame(brand_mapping)
        
        df_purchases = pd.merge(df_trans, df_mapping[['brand_name', 'section']], on='brand_name', how='left')
        
        # 2. Get CCTV Data (Sessions & Events)
        sessions_result = await self.db.execute(select(VisitorSession).where(VisitorSession.store_id == str(store_id)))
        sessions = sessions_result.scalars().all()
        
        events_result = await self.db.execute(select(Event))
        events = events_result.scalars().all()
        
        # 3. Calculate Metrics
        section_metrics = self._calculate_section_metrics(df_purchases, sessions, events)
        opportunity_zones = self._identify_opportunity_zones(section_metrics)
        checkout_intelligence = self._calculate_checkout_intelligence(df_purchases, events)

        return ShopperBehaviorReport(
            sections=section_metrics,
            opportunity_zones=opportunity_zones,
            checkout_intelligence=checkout_intelligence
        )

    def _calculate_section_metrics(self, df_purchases: pd.DataFrame, sessions: List[VisitorSession], events: List[Event]) -> List[SectionBehaviorMetrics]:
        """
        Calculates traffic and conversion metrics for each section.
        """
        # Purchase counts per section from real data
        purchase_counts = df_purchases.groupby('section')['order_id'].nunique().to_dict()

        # Compute zone metrics from visitor sessions
        zone_effectiveness = ConversionEngine.calculate_zone_effectiveness(sessions)

        def map_zone_to_section(zone_name: str) -> str:
            name = zone_name.upper().replace("ZONE_", "").strip()
            if "SKINCARE" in name or "SKIN" in name:
                return "SKINCARE_WALL"
            if "MAKEUP" in name or "COSMETICS" in name:
                return "MAKEUP_WALL"
            if "CENTRAL" in name:
                return "CENTRAL_DISPLAY"
            if "PMU" in name:
                return "PMU_SECTION"
            return zone_name

        visitor_counts = {}
        dwell_sums = {}

        for zone_id, stats in zone_effectiveness.items():
            section = map_zone_to_section(zone_id)
            visitor_counts[section] = visitor_counts.get(section, 0) + stats["visitors_count"]
            dwell_sums[section] = dwell_sums.get(section, 0.0) + (stats["average_dwell_ms"] * stats["visitors_count"])

        # Average dwell times per section (weighted by visitor counts)
        dwell_times = {}
        for section, total_dwell_ms in dwell_sums.items():
            visitors_in_section = visitor_counts.get(section, 0)
            dwell_times[section] = (total_dwell_ms / visitors_in_section / 1000.0) if visitors_in_section > 0 else 0.0

        all_sections = set(purchase_counts.keys()) | set(visitor_counts.keys())
        
        metrics = []
        for section in all_sections:
            visitors = visitor_counts.get(section, 0)
            purchases = purchase_counts.get(section, 0)
            
            metrics.append(SectionBehaviorMetrics(
                section_name=section,
                visitor_count=visitors,
                avg_dwell_seconds=round(dwell_times.get(section, 0.0), 2),
                purchase_count=purchases,
                conversion_rate=purchases / visitors if visitors > 0 else 0.0
            ))
        return metrics

    def _identify_opportunity_zones(self, section_metrics: List[SectionBehaviorMetrics]) -> List[OpportunityZone]:
        """
        Identifies sections with high dwell time but low conversion.
        """
        if not section_metrics:
            return []
            
        opportunity_zones = []
        for m in section_metrics:
            # Threshold: average dwell > 15s and conversion rate < 25% (0.25)
            if m.visitor_count > 0 and m.avg_dwell_seconds > 15.0 and m.conversion_rate < 0.25:
                opportunity_zones.append(OpportunityZone(
                    section_name=m.section_name,
                    recommendation=f"High interest ({m.avg_dwell_seconds:.1f}s avg dwell) but low conversion ({m.conversion_rate * 100:.1f}%). Optimize visual merchandising, product placement, or staff assistance."
                ))
        return opportunity_zones

    def _calculate_checkout_intelligence(self, df_purchases: pd.DataFrame, events: List[Event]) -> CheckoutIntelligence:
        """
        Analyzes checkout queue behavior.
        """
        # Real data from transactions
        completed_purchases = df_purchases['order_id'].nunique()
        
        # This would come from CCTV events. Since data is unavailable, it's 0.
        queue_entries = len([e for e in events if e.event_type == EventType.BILLING_QUEUE_JOIN])

        abandoned_carts = queue_entries - completed_purchases if queue_entries > completed_purchases else 0
        abandonment_rate = abandoned_carts / queue_entries if queue_entries > 0 else 0.0
        
        store_abv = df_purchases['nmv'].sum() / completed_purchases if completed_purchases > 0 else 0
        estimated_lost_revenue = abandoned_carts * store_abv

        return CheckoutIntelligence(
            queue_entries=queue_entries,
            completed_purchases=completed_purchases,
            abandonment_rate=abandonment_rate,
            estimated_lost_revenue=estimated_lost_revenue
        )

    async def get_behavior_insights_for_dashboard(self, store_id: str) -> BehaviorInsights:
        """
        Generates a summary of behavior insights for the executive dashboard.
        """
        report = await self.get_shopper_behavior_report(store_id)
        
        if not report.sections:
            return BehaviorInsights()

        # Filter for sections with actual visitors to get meaningful insights
        active_sections = [s for s in report.sections if s.visitor_count > 0]

        if not active_sections:
            return BehaviorInsights()

        best_converting = max(active_sections, key=lambda s: s.conversion_rate)
        worst_converting = min(active_sections, key=lambda s: s.conversion_rate)
        highest_dwell = max(active_sections, key=lambda s: s.avg_dwell_seconds)

        return BehaviorInsights(
            best_converting_section=best_converting.section_name,
            worst_converting_section=worst_converting.section_name,
            highest_dwell_section=highest_dwell.section_name
        )
