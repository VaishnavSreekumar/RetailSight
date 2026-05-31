from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import aiofiles
import json

from app.models.brigade_transaction import BrigadeTransaction
from app.config import BRAND_TO_SECTION_MAPPING_PATH
from app.schemas.executive_dashboard import (
    ExecutiveDashboard, RevenueMetrics, SectionMetrics, BrandMetrics,
    SalespersonMetrics, CustomerBehavior, LayoutInsights
)

class ExecutiveDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_data(self, store_id: str) -> ExecutiveDashboard:
        """
        Orchestrates the generation of the executive dashboard data.
        """
        result = await self.db.execute(select(BrigadeTransaction))
        transactions = result.scalars().all()
        
        if not transactions:
            # Return a default empty dashboard if no data is available
            return ExecutiveDashboard(
                revenue=RevenueMetrics(nmv=0, gmv=0, abv=0),
                sections=[],
                top_brands=[],
                top_salespeople=[],
                customer_behavior=CustomerBehavior(visitors=0, engaged_visitors=0, conversion_rate=0),
                layout_insights=LayoutInsights(highest_revenue_section="", lowest_revenue_section="", highest_abv_section="")
            )

        df_transactions = pd.DataFrame([t.__dict__ for t in transactions])

        async with aiofiles.open(BRAND_TO_SECTION_MAPPING_PATH, 'r') as f:
            content = await f.read()
            brand_mapping_list = json.loads(content)
        df_mapping = pd.DataFrame(brand_mapping_list)

        # Merge dataframes
        df_merged = pd.merge(
            df_transactions,
            df_mapping[['brand_name', 'section']],
            on='brand_name',
            how='left'
        )

        revenue_metrics = self._get_revenue_metrics(df_transactions)
        section_metrics = self._get_section_metrics(df_merged)
        top_brands = self._get_top_brands(df_transactions)
        top_salespeople = self._get_top_salespeople(df_transactions)
        customer_behavior = self._get_customer_behavior() # No real data source yet
        layout_insights = self._get_layout_insights(section_metrics)

        return ExecutiveDashboard(
            revenue=revenue_metrics,
            sections=section_metrics,
            top_brands=top_brands,
            top_salespeople=top_salespeople,
            customer_behavior=customer_behavior,
            layout_insights=layout_insights
        )

    def _get_revenue_metrics(self, df: pd.DataFrame) -> RevenueMetrics:
        total_nmv = df['nmv'].sum()
        total_gmv = df['gmv'].sum()
        transaction_count = len(df['order_id'].unique())
        abv = total_nmv / transaction_count if transaction_count > 0 else 0
        return RevenueMetrics(nmv=total_nmv, gmv=total_gmv, abv=abv)

    def _get_section_metrics(self, df: pd.DataFrame) -> List[SectionMetrics]:
        section_groups = df.groupby('section')
        
        metrics = []
        for name, group in section_groups:
            nmv = group['nmv'].sum()
            gmv = group['gmv'].sum()
            transaction_count = group['order_id'].nunique()
            abv = nmv / transaction_count if transaction_count > 0 else 0
            metrics.append(SectionMetrics(
                section_name=name,
                nmv=nmv,
                gmv=gmv,
                transaction_count=transaction_count,
                abv=abv
            ))
        return sorted(metrics, key=lambda x: x.nmv, reverse=True)

    def _get_top_brands(self, df: pd.DataFrame) -> List[BrandMetrics]:
        brand_groups = df.groupby('brand_name')
        
        metrics = []
        for name, group in brand_groups:
            nmv = group['nmv'].sum()
            metrics.append(BrandMetrics(brand_name=name, nmv=nmv))
            
        return sorted(metrics, key=lambda x: x.nmv, reverse=True)[:5]

    def _get_top_salespeople(self, df: pd.DataFrame) -> List[SalespersonMetrics]:
        """Calculates top 5 salespeople based on NMV."""
        if 'salesperson_name' not in df.columns or df['salesperson_name'].isnull().all():
            return []

        sales_groups = df.groupby('salesperson_name')
        
        metrics = []
        for name, group in sales_groups:
            total_nmv = group['nmv'].sum()
            units_sold = group['qty'].sum()
            metrics.append(SalespersonMetrics(
                name=name,
                sales_value=total_nmv,
                units_sold=int(units_sold)
            ))
            
        return sorted(metrics, key=lambda x: x.sales_value, reverse=True)[:5]

    def _get_customer_behavior(self) -> Optional[CustomerBehavior]:
        """
        Returns customer behavior metrics.
        NOTE: This data is not available in the Brigade dataset, so this returns None.
        """
        return None

    def _get_layout_insights(self, sections: List[SectionMetrics]) -> LayoutInsights:
        if not sections:
            return LayoutInsights(highest_revenue_section="", lowest_revenue_section="", highest_abv_section="")

        highest_rev_section = max(sections, key=lambda x: x.nmv)
        lowest_rev_section = min(sections, key=lambda x: x.nmv)
        highest_abv_section = max(sections, key=lambda x: x.abv)

        return LayoutInsights(
            highest_revenue_section=highest_rev_section.section_name,
            lowest_revenue_section=lowest_rev_section.section_name,
            highest_abv_section=highest_abv_section.section_name
        )
